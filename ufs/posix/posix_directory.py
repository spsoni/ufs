import os.path
import shutil
from pathlib import PosixPath
from typing import Union

from ufs.base import Directory, File
from ufs.posix.posix_common import (
    file_counter,
    get_dir_size,
    get_files_list,
    PosixObject,
)


class PosixDirectory(PosixObject, Directory):
    def __init__(self, path: Union[str, PosixPath], *args, **kwargs):
        if not str(path).strip().endswith("/"):
            path = path.strip() + "/"
        super().__init__(path, *args, **kwargs)

    def _validate_path(self, path: str) -> bool:
        return path.startswith("/") and path.endswith("/")

    def is_directory_path(self) -> bool:
        return True

    def create(self, parents: bool = True, exist_ok: bool = False, *args, **kwargs):
        PosixPath(self).mkdir(parents=parents, exist_ok=exist_ok)

    def duplicate(self, dst: "Directory", dir_exist_ok: bool = False):
        shutil.copytree(self, dst, dirs_exist_ok=dir_exist_ok)

    def join_as_file(self, *other) -> "File":
        from ufs.posix.posix_file import PosixFile

        return PosixFile(PosixPath(self).joinpath(*other))

    def join_as_directory(self, *other) -> "Directory":
        return PosixDirectory(PosixPath(self).joinpath(*other))

    def remove(self, missing_ok: bool = True, dry_run: bool = False, *args, **kwargs):
        if not dry_run:
            return PosixPath(self).unlink(missing_ok)

        for file_path in self.list_files(recursive=True):
            print(f"Deleting: {file_path}")

    def list_files(self, recursive: bool = True, limit: int = -1, *args, **kwargs):
        # Note: limit do not allow correct sorting order
        return sorted(get_files_list(str(self), recursive=recursive, limit=limit))

    def list_file_objects(
            self, recursive: bool = True, limit: int = -1, *args, **kwargs
    ) -> list:
        from ufs.posix.posix_file import PosixFile

        files = self.list_files(recursive, limit=limit, *args, **kwargs)
        return [PosixFile(f) for f in files]

    def copy_to(self, dst: "Directory", dir_exist_ok: bool = False):
        base_name = os.path.basename(self)
        dst = dst.join_as_directory(base_name)
        shutil.copytree(self, dst, dirs_exist_ok=dir_exist_ok)

    def zip_to(self, dst: File):
        assert dst.endswith(".zip")
        base_name = str(dst).replace(".zip", "")
        shutil.make_archive(base_name=base_name, format="tar", root_dir=self)

    def tar_gz_to(self, dst: File):
        assert dst.endswith(".tar.gz")
        base_name = str(dst).replace(".tar.gz", "")
        shutil.make_archive(base_name=base_name, format="gztar", root_dir=self)

    def file_count(self) -> int:
        return file_counter(str(self))

    def size(self) -> int:
        return get_dir_size(str(self))

    def exists(self) -> bool:
        return PosixPath(self).exists()
