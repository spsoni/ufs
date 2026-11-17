from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from ufs.base import CHUNK_SIZE, File
from ufs.exceptions import UnsupportedOperationError
from ufs.s3.s3_common import S3Object, is_not_found

if TYPE_CHECKING:
    from ufs.posix.posix_common import PosixObject

logger = logging.getLogger(__name__)


def _check_write_mode(mode: str) -> None:
    mode = mode.upper()
    if mode == "APPEND":
        raise UnsupportedOperationError("S3 objects cannot be appended to")
    if mode not in ("WRITE", "OVERWRITE"):
        raise UnsupportedOperationError(f"Unsupported mode: {mode!r}")


class S3File(S3Object, File):
    """An object in an S3 bucket, e.g. ``s3://bucket/path/to/file.txt``."""

    def _validate_path(self, path: str) -> bool:
        key = path.removeprefix(self._protocol).partition("/")[2]
        return bool(key) and super()._validate_path(path)

    def _download(self, dst: PosixObject) -> None:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(Bucket=self.bucket_name, Key=self.prefix, Filename=str(dst))

    def _upload(self, src: PosixObject) -> None:
        self.client.upload_file(Filename=str(src), Bucket=self.bucket_name, Key=self.prefix)

    def size(self) -> int:
        response = self.client.head_object(Bucket=self.bucket_name, Key=self.prefix)
        return int(response["ContentLength"])

    def exists(self) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=self.prefix)
        except Exception as exc:
            if is_not_found(exc):
                return False
            raise
        return True

    def write_text(self, content: str, mode: str = "WRITE", encoding: str = "utf-8") -> None:
        self.write_bytes(content.encode(encoding), mode)

    def write_bytes(self, content: bytes, mode: str = "WRITE") -> None:
        _check_write_mode(mode)
        self.client.put_object(Bucket=self.bucket_name, Key=self.prefix, Body=content)

    def touch(self, exist_ok: bool = True) -> None:
        if self.exists():
            if not exist_ok:
                raise FileExistsError(self._path)
            return
        self.write_bytes(b"")

    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> None:
        if not missing_ok and not self.exists():
            raise FileNotFoundError(self._path)
        if dry_run:
            logger.info("Deleting (dry run): %s", self)
            return
        self.client.delete_object(Bucket=self.bucket_name, Key=self.prefix)

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.read_bytes().decode(encoding)

    def read_bytes(self) -> bytes:
        response = self.client.get_object(Bucket=self.bucket_name, Key=self.prefix)
        data: bytes = response["Body"].read()
        return data

    def _iter_chunks(self) -> Iterator[bytes]:
        response = self.client.get_object(Bucket=self.bucket_name, Key=self.prefix)
        yield from response["Body"].iter_chunks(CHUNK_SIZE)

    def duplicate(self, dst: File) -> File:
        from ufs.posix.posix_file import PosixFile

        if isinstance(dst, PosixFile):
            self._download(dst)
        elif isinstance(dst, S3File):
            self.client.copy(
                CopySource={"Bucket": self.bucket_name, "Key": self.prefix},
                Bucket=dst.bucket_name,
                Key=dst.prefix,
            )
        else:
            raise UnsupportedOperationError(f"Cannot copy {self!r} to {dst!r}")
        return dst
