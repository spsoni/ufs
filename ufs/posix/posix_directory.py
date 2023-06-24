import os.path
import shutil
from pathlib import PosixPath
from typing import Union
from uuid import uuid4

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

    def archive_to_posix(self, dst: File, archive_format: str):
        extension = ''
        if archive_format == 'zip':
            assert dst.endswith(".zip")
            extension = '.zip'
        elif archive_format == 'gztar':
            assert dst.endswith('.tar.gz')
            extension = '.tar.gz'
        else:
            raise RuntimeError(f'Un-supported archive format: {archive_format}')

        base_name = str(dst).replace(extension, "")
        shutil.make_archive(base_name=base_name, format=archive_format, root_dir=self)

    def archive_to_s3(self, dst: File, archive_format: str):
        from ufs.posix.posix_file import PosixFile
        temp_file = PosixFile(os.path.join(f'/tmp/{uuid4()}', os.path.basename(dst)))
        self.archive_to_posix(temp_file, archive_format)
        dst._upload(temp_file)

    def file_count(self) -> int:
        return file_counter(str(self))

    def size(self) -> int:
        return get_dir_size(str(self))

    def exists(self) -> bool:
        return PosixPath(self).exists()
