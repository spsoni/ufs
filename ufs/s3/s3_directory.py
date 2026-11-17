from __future__ import annotations

import posixpath
import tempfile
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from ufs.base import ArchiveFormat, Directory, File
from ufs.exceptions import UnsupportedOperationError
from ufs.s3.s3_common import S3Object, delete_s3_objects
from ufs.s3.s3_file import S3File

if TYPE_CHECKING:
    from ufs.posix.posix_common import PosixObject


class S3Directory(S3Object, Directory):
    """A key prefix in an S3 bucket, e.g. ``s3://bucket/path/``. Its path always ends with ``/``.

    Keys ending in ``/`` are treated as directory markers, not files.
    """

    def _iter_objects(self, recursive: bool = True) -> Iterator[dict[str, Any]]:
        """Yield the ``list_objects_v2`` content entries under this prefix (incl. markers)."""
        paginator = self.client.get_paginator("list_objects_v2")
        kwargs: dict[str, Any] = {"Bucket": self.bucket_name, "Prefix": self.prefix}
        if not recursive:
            kwargs["Delimiter"] = "/"
        for page in paginator.paginate(**kwargs):
            yield from page.get("Contents", [])

    def _iter_file_keys(self, recursive: bool = True) -> Iterator[str]:
        for obj in self._iter_objects(recursive):
            if not obj["Key"].endswith("/"):
                yield obj["Key"]

    def size(self) -> int:
        return sum(int(obj["Size"]) for obj in self._iter_objects())

    def exists(self) -> bool:
        response = self.client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=self.prefix, MaxKeys=1
        )
        return int(response.get("KeyCount", 0)) > 0

    def create(self, parents: bool = True, exist_ok: bool = False) -> None:
        if self.keep_directories_logical:
            return
        if not exist_ok and self.exists():
            raise FileExistsError(self._path)
        self.client.put_object(Bucket=self.bucket_name, Key=self.prefix, Body=b"")

    def duplicate(self, dst: Directory, dir_exist_ok: bool = False) -> Directory:
        from ufs.posix.posix_directory import PosixDirectory

        if isinstance(dst, PosixDirectory):
            if dst.exists() and not dir_exist_ok:
                raise FileExistsError(str(dst))
            self._download(dst)
        elif isinstance(dst, S3Directory):
            for key in self._iter_file_keys():
                target = dst.join_as_file(key.removeprefix(self.prefix))
                self.client.copy(
                    CopySource={"Bucket": self.bucket_name, "Key": key},
                    Bucket=target.bucket_name,
                    Key=target.prefix,
                )
        else:
            raise UnsupportedOperationError(f"Cannot copy {self!r} to {dst!r}")
        return dst

    def _join(self, other: tuple[str, ...]) -> str:
        return posixpath.join(self._path, *(p.lstrip("/") for p in other))

    def join_as_file(self, *other: str) -> S3File:
        return S3File(self._join(other), **self._options())

    def join_as_directory(self, *other: str) -> S3Directory:
        return S3Directory(self._join(other), **self._options())

    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> list[str]:
        keys = [obj["Key"] for obj in self._iter_objects()]
        if not keys and not missing_ok:
            raise FileNotFoundError(self._path)
        delete_s3_objects(self.client, self.bucket_name, keys, dry_run=dry_run)
        return [self._url(key) for key in keys if not key.endswith("/")]

    def list_files(self, recursive: bool = True, limit: int = -1) -> list[str]:
        files: list[str] = []
        for key in self._iter_file_keys(recursive):
            files.append(self._url(key))
            if 0 < limit <= len(files):
                break
        return files

    def list_file_objects(self, recursive: bool = True, limit: int = -1) -> list[File]:
        return [S3File(path, **self._options()) for path in self.list_files(recursive, limit=limit)]

    def archive_to_posix(self, dst: File, archive_format: ArchiveFormat) -> None:
        from ufs.posix.posix_directory import PosixDirectory

        with tempfile.TemporaryDirectory() as tmp:
            staging = PosixDirectory(tmp)
            self._download(staging)
            staging.archive_to_posix(dst, archive_format)

    def file_count(self) -> int:
        return sum(1 for _ in self._iter_file_keys())

    def _download(self, dst: PosixObject) -> None:
        """Download every file under this prefix into the local directory ``dst``.

        ``s3://bucket/path/sub/file1.txt`` downloaded from ``s3://bucket/path/`` into
        ``/tmp/somewhere/`` lands at ``/tmp/somewhere/sub/file1.txt``.
        """
        target_dir = dst.as_directory()
        target_dir.create(exist_ok=True)
        for key in self._iter_file_keys():
            target = target_dir.join_as_file(key.removeprefix(self.prefix))
            target.path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(Bucket=self.bucket_name, Key=key, Filename=str(target))

    def _upload(self, src: PosixObject) -> None:
        """Upload every file under the local directory ``src`` beneath this prefix.

        ``/tmp/somewhere/sub/file1.txt`` uploaded from ``/tmp/somewhere/`` into
        ``s3://bucket/upload_to/`` lands at ``s3://bucket/upload_to/sub/file1.txt``.
        """
        source_dir = src.as_directory()
        for file_path in source_dir.list_files(recursive=True):
            key = self.prefix + file_path.removeprefix(str(source_dir))
            self.client.upload_file(Filename=file_path, Bucket=self.bucket_name, Key=key)
