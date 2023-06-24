import os
from abc import ABC, abstractmethod
from pathlib import PosixPath
from typing import Union


class FileSystemObject(os.PathLike, ABC):
    def __init__(self, path: Union[str, PosixPath], *args, **kwargs):
        self._path = str(path).strip()

    def __str__(self):
        return self._path

    @abstractmethod
    def _validate_path(self, path) -> bool:
        raise NotImplementedError

    def __fspath__(self):
        return self._path

    @abstractmethod
    def size(self) -> int:
        raise NotImplementedError

    def __getattr__(self, item):
        if item in ("startswith", "endswith", "replace"):
            return getattr(self._path, item)

        raise AttributeError(f"Unknown attribute: {item} for {self.__class__}")

    def basename(self) -> str:
        return os.path.basename(self._path)

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError

    def is_file_path(self) -> bool:
        return False

    def is_directory_path(self) -> bool:
        return False

    @abstractmethod
    def as_file(self) -> "File":
        raise NotImplementedError

    @abstractmethod
    def as_directory(self) -> "Directory":
        raise NotImplementedError


class File(FileSystemObject, ABC):
    @abstractmethod
    def write_text(self, content, mode, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def write_bytes(self, content, mode, encoding="utf-8", *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def touch(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def remove(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def read_text(self):
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self):
        raise NotImplementedError

    @abstractmethod
    def checksum(self, *args, **kwargs) -> str:
        raise NotImplementedError

    @abstractmethod
    def duplicate(self, dst: "File"):
        raise NotImplementedError

    @abstractmethod
    def copy_to(self, dst: "Directory"):
        raise NotImplementedError


class DirectoryPrefix(FileSystemObject, ABC):
    @abstractmethod
    def remove(self, missing_ok: bool = True, dry_run: bool = False, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list_files(
            self, recursive: bool = True, limit: int = -1, *args, **kwargs
    ) -> list:
        raise NotImplementedError

    @abstractmethod
    def list_file_objects(self, recursive: bool = True, *args, **kwargs) -> list:
        raise NotImplementedError

    @abstractmethod
    def copy_to(self, dst: "Directory", dir_exist_ok: bool = False):
        raise NotImplementedError

    @abstractmethod
    def archive_to_posix(self, dst: File, archive_format: str):
        raise NotImplementedError

    @abstractmethod
    def archive_to_s3(self, dst: File, archive_format: str):
        raise NotImplementedError

    @abstractmethod
    def file_count(self) -> int:
        raise NotImplementedError


class Directory(DirectoryPrefix, ABC):
    @abstractmethod
    def create(self, parents: bool = True, exist_ok: bool = False, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def duplicate(self, dst: "Directory", dir_exist_ok: bool = False):
        raise NotImplementedError

    @abstractmethod
    def join_as_file(self, *other) -> "File":
        raise NotImplementedError

    @abstractmethod
    def join_as_directory(self, *other) -> "Directory":
        raise NotImplementedError


class FileSystem:
    @staticmethod
    def to_file(path: str):
        if path.strip().startswith("/"):
            from ufs.posix.posix_file import PosixFile

            return PosixFile(path)
        elif path.strip().startswith("s3://") or path.strip().startswith("s3a://"):
            from ufs.s3.s3_file import S3File

            return S3File(path)
        raise RuntimeError(f"Unknown filesystem path: {path}")

    @staticmethod
    def to_directory(path):
        if path.strip().startswith("/"):
            from ufs.posix.posix_directory import PosixDirectory

            return PosixDirectory(path)
        elif path.strip().startswith("s3://") or path.strip().startswith("s3a://"):
            from ufs.s3.s3_directory import S3Directory

            return S3Directory(path)
        raise RuntimeError(f"Unknown filesystem path: {path}")

    @staticmethod
    def to_directory_prefix(path):
        if path.strip().startswith("/"):
            from ufs.posix.posix_directory_prefix import PosixDirectoryPrefix

            return PosixDirectoryPrefix(path)
        elif path.strip().startswith("s3://") or path.strip().startswith("s3a://"):
            from ufs.s3.s3_directory_prefix import S3DirectoryPrefix

            return S3DirectoryPrefix(path)
        raise RuntimeError(f"Unknown filesystem path: {path}")


FS = FileSystem
