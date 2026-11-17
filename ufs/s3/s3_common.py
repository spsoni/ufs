from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from ufs.base import S3_PROTOCOLS, FileSystemObject
from ufs.exceptions import FileSystemException, InvalidPathError

if TYPE_CHECKING:
    from ufs.posix.posix_common import PosixObject
    from ufs.s3.s3_directory import S3Directory
    from ufs.s3.s3_file import S3File

logger = logging.getLogger(__name__)

#: Maximum number of keys accepted by a single S3 DeleteObjects call.
DELETE_BATCH_SIZE = 1000


class S3Object(FileSystemObject, ABC):
    """A path in an S3 bucket.

    :param s3_client: a boto3 S3 client. When omitted, ``boto3.client("s3")`` is created
        lazily on first use (requires ``pip install 'ufs[s3]'``).
    :param protocol: ``"s3://"`` or ``"s3a://"``; paths using the other one are rewritten.
    :param keep_directories_logical: when true (the default) directories are implicit and
        ``create()`` is a no-op; otherwise ``create()`` writes a ``prefix/`` marker object.
    """

    scheme = "s3"

    def __init__(
        self,
        path: str,
        s3_client: Any = None,
        protocol: str = "s3://",
        keep_directories_logical: bool = True,
    ) -> None:
        if protocol not in S3_PROTOCOLS:
            raise InvalidPathError(f"Unsupported protocol {protocol!r}; use one of {S3_PROTOCOLS}")
        self._protocol = protocol
        self._client = s3_client
        self.keep_directories_logical = keep_directories_logical

        super().__init__(path)

        bucket_name, _, prefix = self._path.removeprefix(protocol).partition("/")
        self.bucket_name = bucket_name
        self.prefix = prefix

    def _normalise(self, path: str) -> str:
        for scheme in S3_PROTOCOLS:
            if path.startswith(scheme):
                path = self._protocol + path.removeprefix(scheme)
                break
        return super()._normalise(path)

    def _validate_path(self, path: str) -> bool:
        bucket = path.removeprefix(self._protocol).partition("/")[0]
        return path.startswith(self._protocol) and bool(bucket) and super()._validate_path(path)

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - depends on environment
                raise ImportError("S3 support requires boto3: pip install 'ufs[s3]'") from exc
            self._client = boto3.client("s3")
        return self._client

    def _options(self) -> dict[str, Any]:
        """Constructor options to propagate to derived S3 objects."""
        return {
            "s3_client": self._client,
            "protocol": self._protocol,
            "keep_directories_logical": self.keep_directories_logical,
        }

    def _url(self, key: str) -> str:
        return f"{self._protocol}{self.bucket_name}/{key}"

    @abstractmethod
    def _download(self, dst: PosixObject) -> None: ...

    @abstractmethod
    def _upload(self, src: PosixObject) -> None: ...

    def as_file(self) -> S3File:
        from ufs.s3.s3_file import S3File

        return S3File(self._path.rstrip("/"), **self._options())

    def as_directory(self) -> S3Directory:
        from ufs.s3.s3_directory import S3Directory

        return S3Directory(self._path, **self._options())


def is_not_found(exc: Exception) -> bool:
    """True if a botocore ``ClientError`` means the object does not exist."""
    response = getattr(exc, "response", None) or {}
    code = str(response.get("Error", {}).get("Code", ""))
    return code in ("404", "NoSuchKey", "NotFound")


def delete_s3_objects(
    s3_client: Any, bucket_name: str, keys: list[str], dry_run: bool = False
) -> None:
    """Delete ``keys`` from ``bucket_name`` in batches of ``DELETE_BATCH_SIZE``."""
    for start in range(0, len(keys), DELETE_BATCH_SIZE):
        batch = keys[start : start + DELETE_BATCH_SIZE]
        if dry_run:
            for key in batch:
                logger.info("Deleting (dry run): s3://%s/%s", bucket_name, key)
            continue
        response = s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
        )
        if errors := response.get("Errors"):
            raise FileSystemException(f"Failed to delete {len(errors)} object(s): {errors[:5]}")
