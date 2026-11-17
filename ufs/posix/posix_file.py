from __future__ import annotations

import logging
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO

from ufs.base import CHUNK_SIZE, BinaryMode, File
from ufs.exceptions import UnsupportedOperationError
from ufs.posix.posix_common import PosixObject, convert_mode

logger = logging.getLogger(__name__)


class PosixFile(PosixObject, File):
    """A file on the local filesystem.

    Writes create missing parent directories, mirroring S3 where "directories" are implicit.
    """

    def _validate_path(self, path: str) -> bool:
        return path.startswith("/") and super()._validate_path(path)

    @property
    def path(self) -> Path:
        """This file as a :class:`pathlib.Path`."""
        return Path(self._path)

    def _open_binary(self, mode: BinaryMode) -> BinaryIO:
        if mode != "rb":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.path.open(mode)

    def write_text(self, content: str, mode: str = "WRITE", encoding: str = "utf-8") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open(convert_mode(mode, "text"), encoding=encoding) as f:
            f.write(content)

    def write_bytes(self, content: bytes, mode: str = "WRITE") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open(convert_mode(mode, "bytes")) as f:
            f.write(content)

    def touch(self, exist_ok: bool = True) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=exist_ok)

    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> None:
        if dry_run:
            logger.info("Deleting (dry run): %s", self)
            return
        self.path.unlink(missing_ok=missing_ok)

    def read_text(self, encoding: str = "utf-8") -> str:
        return self.path.read_text(encoding=encoding)

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()

    def _iter_chunks(self) -> Iterator[bytes]:
        with self.path.open("rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    def duplicate(self, dst: File) -> File:
        from ufs.s3.s3_file import S3File

        if isinstance(dst, PosixFile):
            dst.path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self, dst)
        elif isinstance(dst, S3File):
            dst._upload(self)
        else:
            raise UnsupportedOperationError(f"Cannot copy {self!r} to {dst!r}")
        return dst

    def size(self) -> int:
        return self.path.stat().st_size

    def exists(self) -> bool:
        return self.path.is_file()
