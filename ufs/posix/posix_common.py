from __future__ import annotations

import os
from abc import ABC
from collections.abc import Iterator
from typing import TYPE_CHECKING

from ufs.base import FileSystemObject
from ufs.exceptions import UnsupportedOperationError

if TYPE_CHECKING:
    from ufs.posix.posix_directory import PosixDirectory
    from ufs.posix.posix_file import PosixFile


class PosixObject(FileSystemObject, ABC):
    scheme = "posix"

    def _normalise(self, path: str) -> str:
        # Relative paths are resolved against the current working directory.
        # abspath (not Path.resolve) leaves symlinks unresolved.
        return super()._normalise(os.path.abspath(path))  # noqa: PTH100

    def as_file(self) -> PosixFile:
        from ufs.posix.posix_file import PosixFile

        return PosixFile(self._path)

    def as_directory(self) -> PosixDirectory:
        from ufs.posix.posix_directory import PosixDirectory

        return PosixDirectory(self._path)


def convert_mode(mode: str, format: str) -> str:
    """Translate a ufs write mode (READ/WRITE/OVERWRITE/APPEND) into an ``open()`` mode."""
    modes = {"READ": "r", "WRITE": "w", "OVERWRITE": "w", "APPEND": "a"}
    try:
        m = modes[mode.upper()]
    except KeyError:
        raise UnsupportedOperationError(f"Unsupported mode: {mode!r}") from None

    if format == "bytes":
        return f"{m}b"
    if format == "text":
        return m
    raise ValueError(f"Invalid format: {format!r}")


def iter_files(path: str, recursive: bool = True) -> Iterator[os.DirEntry[str]]:
    """Yield a ``DirEntry`` for every regular file under ``path``."""
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                yield entry
            elif recursive and entry.is_dir(follow_symlinks=False):
                yield from iter_files(entry.path, recursive)
