import os
from abc import ABC, abstractmethod


class FileSystemObject(os.PathLike, ABC):
    def __init__(self, path, *args, **kwargs):
        self._path = str(path).strip()

    @abstractmethod
    def _validate_path(self, path) -> bool:
        raise NotImplementedError

    def __fspath__(self):
        return self._path

    @abstractmethod
    def size(self) -> int:
        raise NotImplementedError

    def basename(self) -> str:
        return os.path.basename(self._path)

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError

    def is_file_path(self) -> bool:
        return False

    def is_directory_path(self) -> bool:
        return False


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
    def checksum(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def duplicate(self, dst: "File"):
        raise NotImplementedError

    @abstractmethod
    def copy_to(self, dst: "Directory"):
        raise NotImplementedError


class DirectoryPrefix(FileSystemObject, ABC):
    @abstractmethod
    def remove(self, missing_ok: bool = True, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list(self, recursive: bool = True, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def copy_to(self, dst: "Directory"):
        raise NotImplementedError

    @abstractmethod
    def zip_to(self, dst: File):
        raise NotImplementedError

    @abstractmethod
    def tar_gz_to(self, dst: File):
        raise NotImplementedError

    @abstractmethod
    def file_count(self) -> int:
        raise NotImplementedError


class Directory(DirectoryPrefix, ABC):
    @abstractmethod
    def create(self, parents: bool = True, exist_ok: bool = False, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def duplicate(self, dst: "Directory"):
        raise NotImplementedError

    @abstractmethod
    def joinpath(self, *other):
        raise NotImplementedError


class FileSystem:
    @staticmethod
    @abstractmethod
    def to_file(path):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_directory(path):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def to_directory_prefix(path):
        raise NotImplementedError


FS = FileSystem
