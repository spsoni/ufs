from __future__ import annotations

import logging
import shutil
from pathlib import Path

from ufs.base import ArchiveFormat, Directory, File, archive_base_name
from ufs.exceptions import UnsupportedOperationError
from ufs.posix.posix_common import PosixObject, iter_files
from ufs.posix.posix_file import PosixFile

logger = logging.getLogger(__name__)


class PosixDirectory(PosixObject, Directory):
    """A directory on the local filesystem. Its path always ends with ``/``."""

    def _validate_path(self, path: str) -> bool:
        return path.startswith("/") and super()._validate_path(path)

    @property
    def path(self) -> Path:
        """This directory as a :class:`pathlib.Path`."""
        return Path(self._path)

    def create(self, parents: bool = True, exist_ok: bool = False) -> None:
        self.path.mkdir(parents=parents, exist_ok=exist_ok)

    def duplicate(self, dst: Directory, dir_exist_ok: bool = False) -> Directory:
        from ufs.s3.s3_directory import S3Directory

        if isinstance(dst, PosixDirectory):
            shutil.copytree(self, dst, dirs_exist_ok=dir_exist_ok)
        elif isinstance(dst, S3Directory):
            dst._upload(self)
        else:
            raise UnsupportedOperationError(f"Cannot copy {self!r} to {dst!r}")
        return dst

    def remove(self, missing_ok: bool = True, dry_run: bool = False) -> list[str]:
        if not self.exists():
            if missing_ok:
                return []
            raise FileNotFoundError(self._path)

        files = self.list_files(recursive=True)
        if dry_run:
            for file_path in files:
                logger.info("Deleting (dry run): %s", file_path)
            return files

        shutil.rmtree(self)
        return files

    def list_files(self, recursive: bool = True, limit: int = -1) -> list[str]:
        files = sorted(entry.path for entry in iter_files(self._path, recursive))
        return files[:limit] if limit > 0 else files

    def archive_to_posix(self, dst: File, archive_format: ArchiveFormat) -> None:
        if not isinstance(dst, PosixFile):
            raise UnsupportedOperationError(f"archive_to_posix needs a PosixFile, got {dst!r}")
        base_name = archive_base_name(dst, archive_format)
        dst.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.make_archive(base_name=base_name, format=archive_format, root_dir=self)

    def file_count(self) -> int:
        return sum(1 for _ in iter_files(self._path))

    def size(self) -> int:
        return sum(entry.stat().st_size for entry in iter_files(self._path))

    def exists(self) -> bool:
        return self.path.is_dir()
