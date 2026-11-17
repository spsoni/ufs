from __future__ import annotations

import hashlib
import os
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from ufs.exceptions import InvalidPathError, UnsupportedOperationError

if TYPE_CHECKING:
    from botocore.client import BaseClient

    from ufs.s3.s3_file import S3File

ArchiveFormat = Literal["zip", "tar", "gztar", "bztar", "xztar"]
ARCHIVE_EXTENSIONS: dict[str, str] = {
    "zip": ".zip",
    "tar": ".tar",
    "gztar": ".tar.gz",
    "bztar": ".tar.bz2",
    "xztar": ".tar.xz",
}

#: Read size used when streaming file contents (e.g. for checksums).
CHUNK_SIZE = 1024 * 1024

S3_PROTOCOLS = ("s3://", "s3a://")


class FileSystemObject(os.PathLike[str], ABC):
    """A path on some filesystem. Behaves like ``os.PathLike`` and compares by path."""

    #: Short identifier of the backing filesystem, e.g. ``"posix"`` or ``"s3"``.
    scheme: ClassVar[str]

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = self._normalise(os.fspath(path).strip())
        if not self._validate_path(self._path):
            raise InvalidPathError(f"Invalid path for {type(self).__name__}: {self._path!r}")

    def _normalise(self, path: str) -> str:
        """Hook for subclasses to canonicalise a path before validation."""
        return path

    def _validate_path(self, path: str) -> bool:
        """Hook for subclasses to reject paths; cooperative via ``super()``."""
        return True

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._path!r})"

    def __fspath__(self) -> str:
        return self._path

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileSystemObject):
            return NotImplemented
        return type(self) is type(other) and self._path == other._path

    def __hash__(self) -> int:
        return hash((type(self), self._path))

    def startswith(self, prefix: str | tuple[str, ...]) -> bool:
        return self._path.startswith(prefix)

    def endswith(self, suffix: str | tuple[str, ...]) -> bool:
        return self._path.endswith(suffix)

    def basename(self) -> str:
        """Final path component, ignoring any trailing ``/`` on directories."""
        return os.path.basename(self._path.rstrip("/"))  # noqa: PTH119 - also used for S3 URLs

    def is_file_path(self) -> bool:
        return False

    def is_directory_path(self) -> bool:
        return False

    @abstractmethod
    def size(self) -> int: ...

    @abstractmethod
    def exists(self) -> bool: ...

    @abstractmethod
    def as_file(self) -> File: ...

    @abstractmethod
    def as_directory(self) -> Directory: ...


class File(FileSystemObject, ABC):
    def _validate_path(self, path: str) -> bool:
        return not path.endswith("/")

    def is_file_path(self) -> bool:
        return True

    @abstractmethod
    def write_text(self, content: str, mode: str = "WRITE", encoding: str = "utf-8") -> None: ...

    @abstractmethod
    def write_bytes(self, content: bytes, mode: str = "WRITE") -> None: ...

    @abstractmethod
    def touch(self, exist_ok: bool = True) -> None: ...

    @abstractmethod
    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> None: ...

    @abstractmethod
    def read_text(self, encoding: str = "utf-8") -> str: ...

    @abstractmethod
    def read_bytes(self) -> bytes: ...

    @abstractmethod
    def _iter_chunks(self) -> Iterable[bytes]:
        """Yield the file contents in chunks of at most ``CHUNK_SIZE`` bytes."""

    def checksum(self, algorithm: str = "sha256") -> str:
        """Hex digest of the file contents, streamed so large files are not held in memory."""
        digest = hashlib.new(algorithm)
        for chunk in self._iter_chunks():
            digest.update(chunk)
        return digest.hexdigest()

    @abstractmethod
    def duplicate(self, dst: File) -> File:
        """Copy this file to the path ``dst`` (on any supported filesystem) and return it."""

    def copy_to(self, dst: Directory) -> File:
        """Copy this file into the directory ``dst``, keeping its basename."""
        return self.duplicate(dst.join_as_file(self.basename()))


class DirectoryPrefix(FileSystemObject, ABC):
    def _normalise(self, path: str) -> str:
        path = super()._normalise(path)
        return path if path.endswith("/") else path + "/"

    def _validate_path(self, path: str) -> bool:
        return path.endswith("/")

    def is_directory_path(self) -> bool:
        return True

    @abstractmethod
    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> list[str]:
        """Delete everything under this directory. Returns the file paths (to be) removed."""

    @abstractmethod
    def list_files(self, recursive: bool = True, limit: int = -1) -> list[str]:
        """Sorted paths of files under this directory; ``limit > 0`` truncates the result."""

    @abstractmethod
    def list_file_objects(self, recursive: bool = True, limit: int = -1) -> list[File]: ...

    @abstractmethod
    def file_count(self) -> int: ...

    @abstractmethod
    def archive_to_posix(self, dst: File, archive_format: ArchiveFormat) -> None: ...

    def archive_to_s3(self, dst: S3File, archive_format: ArchiveFormat) -> None:
        from ufs.posix.posix_file import PosixFile

        with tempfile.TemporaryDirectory() as tmp:
            staged = PosixFile(Path(tmp) / dst.basename())
            self.archive_to_posix(staged, archive_format)
            dst._upload(staged)

    def archive_to(self, dst: File, archive_format: ArchiveFormat) -> None:
        """Archive this directory into ``dst`` on whichever filesystem ``dst`` lives."""
        from ufs.s3.s3_file import S3File

        if isinstance(dst, S3File):
            self.archive_to_s3(dst, archive_format)
        else:
            self.archive_to_posix(dst, archive_format)


class Directory(DirectoryPrefix, ABC):
    @abstractmethod
    def create(self, parents: bool = True, exist_ok: bool = False) -> None: ...

    @abstractmethod
    def duplicate(self, dst: Directory, dir_exist_ok: bool = False) -> Directory:
        """Copy the contents of this directory into ``dst`` and return it."""

    def copy_to(self, dst: Directory, dir_exist_ok: bool = False) -> Directory:
        """Copy this directory into ``dst`` as a sub-directory with the same basename."""
        return self.duplicate(dst.join_as_directory(self.basename()), dir_exist_ok=dir_exist_ok)

    @abstractmethod
    def join_as_file(self, *other: str) -> File: ...

    @abstractmethod
    def join_as_directory(self, *other: str) -> Directory: ...


def archive_base_name(dst: File, archive_format: str) -> str:
    """Path of ``dst`` without its archive extension, as ``shutil.make_archive`` expects."""
    try:
        extension = ARCHIVE_EXTENSIONS[archive_format]
    except KeyError:
        raise UnsupportedOperationError(
            f"Unsupported archive format {archive_format!r}; "
            f"expected one of {sorted(ARCHIVE_EXTENSIONS)}"
        ) from None
    path = str(dst)
    if not path.endswith(extension):
        raise InvalidPathError(f"{archive_format} archive path must end with {extension!r}: {path}")
    return path.removesuffix(extension)


def _is_s3(path: str) -> bool:
    return path.startswith(S3_PROTOCOLS)


class FileSystem:
    """Factory that picks the right implementation from the path."""

    @staticmethod
    def to_file(path: str | os.PathLike[str], *, s3_client: BaseClient | Any = None) -> File:
        path = os.fspath(path).strip()
        if _is_s3(path):
            from ufs.s3.s3_file import S3File

            return S3File(path, s3_client=s3_client)
        from ufs.posix.posix_file import PosixFile

        return PosixFile(path)

    @staticmethod
    def to_directory(
        path: str | os.PathLike[str], *, s3_client: BaseClient | Any = None
    ) -> Directory:
        path = os.fspath(path).strip()
        if _is_s3(path):
            from ufs.s3.s3_directory import S3Directory

            return S3Directory(path, s3_client=s3_client)
        from ufs.posix.posix_directory import PosixDirectory

        return PosixDirectory(path)


FS = FileSystem
