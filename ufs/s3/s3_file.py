from ufs.base import File
from ufs.s3.s3_common import S3Object


class S3File(S3Object, File):
    def is_file_path(self) -> bool:
        return True

    def write_text(self, content, mode, *args, **kwargs):
        pass

    def write_bytes(self, content, mode, encoding="utf-8", *args, **kwargs):
        pass

    def touch(self, *args, **kwargs):
        pass

    def remove(self, missing_ok: bool = True, *args, **kwargs):
        pass

    def read_text(self):
        pass

    def read_bytes(self):
        pass

    def checksum(self, *args, **kwargs):
        pass

    def duplicate(self, dst: "File"):
        pass

    def copy_to(self, dst: "Directory"):
        pass

    def size(self) -> int:
        pass

    def exists(self) -> bool:
        pass
