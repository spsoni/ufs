from ufs.base import DirectoryPrefix, File
from ufs.s3.s3_common import S3Object


class S3DirectoryPrefix(S3Object, DirectoryPrefix):
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
