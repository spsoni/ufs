from pathlib import PosixPath

from ufs.base import Directory, File


class PosixDirectory(Directory):
    def is_directory_path(self) -> bool:
        return True

    def create(self, parents: bool = True, exist_ok: bool = False, *args, **kwargs):
        PosixPath(self).mkdir(parents=parents, exist_ok=exist_ok)

    def duplicate(self, dst: "Directory"):
        pass

    def joinpath(self, *other):
        return PosixPath(self).joinpath(*other)

    def remove(self, missing_ok: bool = True, *args, **kwargs):
        PosixPath(self).unlink(missing_ok)

    def list(self, recursive: bool = True, *args, **kwargs):
        pass

    def copy_to(self, dst: "Directory"):
        pass

    def zip_to(self, dst: File):
        pass

    def tar_gz_to(self, dst: File):
        pass

    def file_count(self) -> int:
        pass

    def size(self) -> int:
        pass

    def exists(self) -> bool:
        return PosixPath(self).exists()
