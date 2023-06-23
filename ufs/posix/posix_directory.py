import os.path
import shutil
from pathlib import PosixPath

from ufs.base import Directory, File
from ufs.posix.posix_common import file_counter, get_dir_size, get_files_list


class PosixDirectory(Directory):
    def __init__(self, path: str, *args, **kwargs):
        if not path.strip().endswith("/"):
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

    def remove(self, missing_ok: bool = True, *args, **kwargs):
        PosixPath(self).unlink(missing_ok)

    def list_files(self, recursive: bool = True, *args, **kwargs):
        return sorted(get_files_list(str(self), recursive=recursive))

    def list_file_objects(self, recursive: bool = True, *args, **kwargs) -> list:
        from ufs.posix.posix_file import PosixFile

        files = self.list_files(recursive, *args, **kwargs)
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
