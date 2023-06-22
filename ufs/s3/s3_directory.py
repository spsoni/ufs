from ufs.base import Directory, File
from ufs.s3.s3_common import S3Object


class S3Directory(S3Object, Directory):
    def is_directory_path(self) -> bool:
        return True

    def create(self, exist_ok: bool = False, *args, **kwargs):
        pass

    def duplicate(self, dst: "Directory"):
        pass

    def joinpath(self, *other):
        pass

    def remove(self, missing_ok: bool = True, *args, **kwargs):
        pass

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
        pass
