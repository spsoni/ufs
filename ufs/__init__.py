"""Unified File System: one object-oriented API for Posix and S3 paths."""

from importlib.metadata import PackageNotFoundError, version

from ufs.base import FS, Directory, DirectoryPrefix, File, FileSystem, FileSystemObject
from ufs.exceptions import FileSystemException, InvalidPathError, UnsupportedOperationError
from ufs.posix.posix_directory import PosixDirectory
from ufs.posix.posix_file import PosixFile
from ufs.s3.s3_directory import S3Directory
from ufs.s3.s3_file import S3File

try:
    __version__ = version("ufs")
except PackageNotFoundError:  # pragma: no cover - running from a source checkout
    __version__ = "0.0.0"

__all__ = [
    "FS",
    "Directory",
    "DirectoryPrefix",
    "File",
    "FileSystem",
    "FileSystemException",
    "FileSystemObject",
    "InvalidPathError",
    "PosixDirectory",
    "PosixFile",
    "S3Directory",
    "S3File",
    "UnsupportedOperationError",
    "__version__",
]
