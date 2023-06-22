from ufs.base import DirectoryPrefix, File


class PosixDirectoryPrefix(DirectoryPrefix):
    def remove(self, *args, **kwargs):
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
