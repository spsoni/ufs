from ufs.base import DirectoryPrefix, File


class PosixDirectoryPrefix(DirectoryPrefix):
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

    def _validate_path(self, path) -> bool:
        pass

    def size(self) -> int:
        pass

    def exists(self) -> bool:
        pass
