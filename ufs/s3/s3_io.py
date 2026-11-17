"""File-like streams over S3 objects, used by :meth:`ufs.S3File.open`."""

from __future__ import annotations

import io
import tempfile
from types import TracebackType
from typing import TYPE_CHECKING, Any

from ufs.base import CHUNK_SIZE

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer as Buffer
    from _typeshed import WriteableBuffer

#: Writes are kept in memory up to this size, then spill to a temporary file.
SPOOL_MAX_SIZE = 8 * 1024 * 1024


class S3ObjectReader(io.RawIOBase):
    """Unbuffered, forward-only reader over a ``get_object`` streaming body."""

    def __init__(self, body: Any) -> None:
        self._body = body

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: WriteableBuffer) -> int:
        view = memoryview(buffer).cast("B")
        data = self._body.read(len(view))
        view[: len(data)] = data
        return len(data)

    def close(self) -> None:
        if not self.closed:
            self._body.close()
        super().close()


def open_reader(client: Any, bucket: str, key: str) -> io.BufferedReader:
    body = client.get_object(Bucket=bucket, Key=key)["Body"]
    return io.BufferedReader(S3ObjectReader(body), buffer_size=CHUNK_SIZE)


class S3ObjectWriter(io.BufferedIOBase):
    """Buffers writes in a spooled temporary file and uploads them on ``close()``.

    If the ``with`` block raises, or :meth:`abort` is called, nothing is uploaded.
    """

    def __init__(self, client: Any, bucket: str, key: str) -> None:
        self._client = client
        self._bucket = bucket
        self._key = key
        # Closed in close(); the writer owns the spool for its whole lifetime.
        self._spool = tempfile.SpooledTemporaryFile(max_size=SPOOL_MAX_SIZE)  # noqa: SIM115
        self._aborted = False

    def writable(self) -> bool:
        return True

    def write(self, data: Buffer) -> int:
        if self.closed:
            raise ValueError("I/O operation on closed file.")
        return self._spool.write(data)

    def abort(self) -> None:
        """Discard everything written so far; ``close()`` will not upload."""
        self._aborted = True

    def close(self) -> None:
        if self.closed:
            return
        try:
            if not self._aborted:
                self._spool.seek(0)
                self._client.upload_fileobj(self._spool, self._bucket, self._key)
        finally:
            self._spool.close()
            super().close()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.abort()
        self.close()
