import os
from abc import ABC

from ufs.base import FileSystemObject


class PosixObject(FileSystemObject, ABC):
    def as_file(self) -> "File":
        from ufs.posix.posix_file import PosixFile

        return PosixFile(self._path)

    def as_directory(self) -> "Directory":
        from ufs.posix.posix_directory import PosixDirectory

        return PosixDirectory(self._path)


def convert_mode(mode: str, format: str) -> str:
    mode = mode.upper()
    m = "r"
    if mode == "READ":
        m = "r"
    elif mode in ("WRITE", "OVERWRITE"):
        m = "w"
    elif mode == "APPEND":
        m = "a"
    else:
        raise RuntimeError(f"Un-supported mode = {mode}")

    if format == "bytes":
        return f"{m}b"
    elif format == "text":
        return m

    raise RuntimeError(f"Invalid format: {format}")


def file_counter(path: str) -> int:
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += 1
            elif entry.is_dir():
                total += file_counter(entry.path)
    return total


def get_files_list(path: str, recursive: bool = True, limit: int = -1) -> list:
    files = list()
    counter = 0

    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                files.append(str(entry.path))
                counter += 1
            elif entry.is_dir() and recursive:
                files.extend(
                    get_files_list(str(entry.path), recursive, limit=(limit - counter))
                )
            if 0 < limit <= counter:
                break

    if 0 < limit < len(files):
        files = files[:limit]

    return files


def get_dir_size(path: str):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total
