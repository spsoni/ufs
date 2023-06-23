from ufs.base import Directory, File
from ufs.s3.s3_common import S3Object


class S3Directory(S3Object, Directory):
    def create(self, parents: bool = True, exist_ok: bool = False, *args, **kwargs):
        pass

    def duplicate(self, dst: "Directory", dir_exist_ok: bool = False):
        pass

    def join_as_file(self, *other) -> "File":
        pass

    def join_as_directory(self, *other) -> "Directory":
        pass

    def remove(self, missing_ok: bool = True, *args, **kwargs):
        pass

    def list_files(self, recursive: bool = True, *args, **kwargs) -> list:
        pass

    def list_file_objects(self, recursive: bool = True, *args, **kwargs) -> list:
        pass

    def copy_to(self, dst: "Directory", dir_exist_ok: bool = False):
        pass

    def zip_to(self, dst: File):
        pass

    def tar_gz_to(self, dst: File):
        pass

    def file_count(self) -> int:
        pass

    def is_directory_path(self) -> bool:
        return True
