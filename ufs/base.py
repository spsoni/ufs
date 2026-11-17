from __future__ import annotations

import fnmatch
import hashlib
import io
import os
import posixpath
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import IO, TYPE_CHECKING, Any, BinaryIO, ClassVar, Literal, TextIO, overload

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

BinaryMode = Literal["rb", "wb", "ab"]
TextMode = Literal["r", "w", "a", "rt", "wt", "at"]

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

    # -- factories implemented by each backend ------------------------------------------

    @abstractmethod
    def _file(self, path: str) -> File:
        """Build a file on the same filesystem (and with the same options) as ``self``."""

    @abstractmethod
    def _directory(self, path: str) -> Directory:
        """Build a directory on the same filesystem (and with the same options) as ``self``."""

    @property
    @abstractmethod
    def _root(self) -> str:
        """The top-most directory path: ``/`` locally, ``s3://bucket/`` on S3."""

    # -- dunder protocol ----------------------------------------------------------------

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

    # -- path helpers -------------------------------------------------------------------

    def startswith(self, prefix: str | tuple[str, ...]) -> bool:
        return self._path.startswith(prefix)

    def endswith(self, suffix: str | tuple[str, ...]) -> bool:
        return self._path.endswith(suffix)

    def basename(self) -> str:
        """Final path component, ignoring any trailing ``/`` on directories."""
        return posixpath.basename(self._path.rstrip("/"))

    @property
    def name(self) -> str:
        """Same as :meth:`basename`, for symmetry with :class:`pathlib.Path`."""
        return self.basename()

    @property
    def parent(self) -> Directory:
        """The containing directory. The root's parent is the root itself."""
        if self._path == self._root:
            return self._directory(self._root)
        return self._directory(posixpath.dirname(self._path.rstrip("/")))

    def is_file_path(self) -> bool:
        return False

    def is_directory_path(self) -> bool:
        return False

    def as_file(self) -> File:
        return self._file(self._path.rstrip("/"))

    def as_directory(self) -> Directory:
        return self._directory(self._path)

    @abstractmethod
    def size(self) -> int:
        """Size in bytes: the file's length, or the total of all files under a directory."""

    @abstractmethod
    def exists(self) -> bool:
        """Whether the file exists, or the directory exists (on S3: has any object under it)."""


class File(FileSystemObject, ABC):
    """Interface shared by :class:`~ufs.PosixFile` and :class:`~ufs.S3File`."""

    def _validate_path(self, path: str) -> bool:
        return not path.endswith("/")

    def is_file_path(self) -> bool:
        return True

    @property
    def suffix(self) -> str:
        """Final extension including the dot, e.g. ``".gz"`` for ``data.tar.gz``."""
        return posixpath.splitext(self.name)[1]

    @property
    def stem(self) -> str:
        """Name without its final extension."""
        return posixpath.splitext(self.name)[0]

    # -- streaming ----------------------------------------------------------------------

    @abstractmethod
    def _open_binary(self, mode: BinaryMode) -> BinaryIO:
        """Open the file as a binary stream in mode ``rb``, ``wb`` or ``ab``."""

    @overload
    def open(self, mode: BinaryMode) -> BinaryIO: ...

    @overload
    def open(
        self,
        mode: TextMode = "r",
        encoding: str = "utf-8",
        errors: str | None = None,
        newline: str | None = None,
    ) -> TextIO: ...

    def open(
        self,
        mode: str = "r",
        encoding: str = "utf-8",
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]:
        """Open the file like the built-in :func:`open`, on any filesystem.

        Supports ``r``/``w``/``a`` in text (default) or binary (``b``) mode. On S3, reads
        stream from the object (the stream is not seekable) and writes are buffered and
        uploaded when the file is closed. Nothing is uploaded if the ``with`` block raises.
        """
        flags = set(mode)
        kinds = flags & {"r", "w", "a"}
        if len(kinds) != 1 or not flags <= {"r", "w", "a", "b", "t"} or {"b", "t"} <= flags:
            raise ValueError(f"Invalid mode: {mode!r}")
        binary_mode: BinaryMode = f"{kinds.pop()}b"  # type: ignore[assignment]
        stream = self._open_binary(binary_mode)
        if "b" in flags:
            return stream
        return _TextStream(stream, encoding=encoding, errors=errors, newline=newline)

    # -- whole-file I/O -----------------------------------------------------------------

    @abstractmethod
    def write_text(self, content: str, mode: str = "WRITE", encoding: str = "utf-8") -> None:
        """Write ``content`` as text.

        :param mode: ``"WRITE"``/``"OVERWRITE"`` replaces the file; ``"APPEND"`` adds to it
            (local files only).
        """

    @abstractmethod
    def write_bytes(self, content: bytes, mode: str = "WRITE") -> None:
        """Write ``content`` as bytes. ``mode`` works as in :meth:`write_text`."""

    @abstractmethod
    def touch(self, exist_ok: bool = True) -> None:
        """Create an empty file if it does not exist. Existing contents are kept.

        :raises FileExistsError: if the file exists and ``exist_ok`` is false.
        """

    @abstractmethod
    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> None:
        """Delete the file.

        :param missing_ok: if false, raise :class:`FileNotFoundError` when it does not exist.
        :param dry_run: only log what would be deleted.
        """

    @abstractmethod
    def read_text(self, encoding: str = "utf-8") -> str:
        """Return the whole file decoded as text."""

    @abstractmethod
    def read_bytes(self) -> bytes:
        """Return the whole file as bytes."""

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


class _TextStream(io.TextIOWrapper):
    """Text wrapper that lets the binary stream discard pending writes on error."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        abort = getattr(self.buffer, "abort", None)
        if exc_type is not None and abort is not None:
            abort()
        super().__exit__(exc_type, exc, tb)


class DirectoryPrefix(FileSystemObject, ABC):
    """Listing, deletion and archiving shared by all directories. Paths end with ``/``."""

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

    def list_file_objects(self, recursive: bool = True, limit: int = -1) -> list[File]:
        """Like :meth:`list_files`, but returns :class:`File` objects."""
        return [self._file(path) for path in self.list_files(recursive, limit=limit)]

    def glob(self, pattern: str, recursive: bool = True) -> list[File]:
        """Files whose path relative to this directory matches the shell-style ``pattern``.

        Matching uses :mod:`fnmatch`, so ``*`` also matches ``/``: ``"*.csv"`` finds CSV
        files at any depth (use ``recursive=False`` for the top level only) and
        ``"2024/*.csv"`` finds those under ``2024/``.
        """
        return [
            self._file(path)
            for path in self.list_files(recursive)
            if fnmatch.fnmatchcase(path.removeprefix(self._path), pattern)
        ]

    @abstractmethod
    def file_count(self) -> int:
        """Number of files under this directory, at any depth."""

    @abstractmethod
    def archive_to_posix(self, dst: File, archive_format: ArchiveFormat) -> None:
        """Archive the directory contents into the local file ``dst``."""

    def archive_to_s3(self, dst: S3File, archive_format: ArchiveFormat) -> None:
        """Archive the directory contents into the S3 object ``dst`` (staged locally)."""
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
    """Interface shared by :class:`~ufs.PosixDirectory` and :class:`~ufs.S3Directory`."""

    @abstractmethod
    def create(self, parents: bool = True, exist_ok: bool = False) -> None:
        """Create the directory. On S3 this is a no-op unless directories are not logical.

        :raises FileExistsError: if it exists and ``exist_ok`` is false.
        """

    @abstractmethod
    def duplicate(self, dst: Directory, dir_exist_ok: bool = False) -> Directory:
        """Copy the contents of this directory into ``dst`` and return it."""

    def copy_to(self, dst: Directory, dir_exist_ok: bool = False) -> Directory:
        """Copy this directory into ``dst`` as a sub-directory with the same basename."""
        return self.duplicate(dst.join_as_directory(self.basename()), dir_exist_ok=dir_exist_ok)

    def _join(self, other: tuple[str, ...]) -> str:
        # Leading slashes are stripped so a part can never escape this directory.
        return posixpath.join(self._path, *(os.fspath(p).lstrip("/") for p in other))

    def join_as_file(self, *other: str) -> File:
        """``directory.join_as_file("a", "b.txt")`` is the file ``<directory>/a/b.txt``."""
        return self._file(self._join(other))

    def join_as_directory(self, *other: str) -> Directory:
        """``directory.join_as_directory("a", "b")`` is the directory ``<directory>/a/b/``."""
        return self._directory(self._join(other))

    def __truediv__(self, other: str) -> File | Directory:
        """``directory / "a.txt"`` is a file; ``directory / "sub/"`` is a directory."""
        if other.endswith("/"):
            return self.join_as_directory(other)
        return self.join_as_file(other)


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
    """Factory that picks the right implementation from the path.

    Paths starting with ``s3://`` or ``s3a://`` map to S3; anything else is a local path.
    ``FS`` is a short alias.
    """

    @staticmethod
    def to_file(path: str | os.PathLike[str], *, s3_client: BaseClient | Any = None) -> File:
        """Return a :class:`File` for ``path``.

        :param s3_client: boto3 S3 client to use for S3 paths (ignored for local paths).
        """
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
        """Return a :class:`Directory` for ``path``. See :meth:`to_file`."""
        path = os.fspath(path).strip()
        if _is_s3(path):
            from ufs.s3.s3_directory import S3Directory

            return S3Directory(path, s3_client=s3_client)
        from ufs.posix.posix_directory import PosixDirectory

        return PosixDirectory(path)


FS = FileSystem
