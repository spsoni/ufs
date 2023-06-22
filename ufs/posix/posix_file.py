from pathlib import PosixPath

from ufs.base import File
from ufs.posix.posix_common import convert_mode


class PosixFile(File):
    def is_file_path(self) -> bool:
        return True

    def write_text(self, content: str, mode, *args, **kwargs):
        mode = convert_mode(mode, "text")
        with open(self, mode) as f:
            f.write(content)

    def write_bytes(self, content: bytes, mode, encoding="utf-8", *args, **kwargs):
        mode = convert_mode(mode, "bytes")
        with open(self, mode) as f:
            f.write(content)

    def touch(self, exist_ok: bool = True, *args, **kwargs):
        PosixPath(self).touch(exist_ok=exist_ok)

    def remove(self, missing_ok: bool = True, *args, **kwargs):
        PosixPath(self).unlink(missing_ok)

    def read_text(self) -> str:
        return open(self).read()

    def read_bytes(self) -> bytes:
        return open(self, "rb").read()

    def checksum(self, *args, **kwargs):
        pass

    def duplicate(self, dst: "File"):
        pass

    def copy_to(self, dst: "Directory"):
        pass

    def size(self) -> int:
        PosixPath(self).stat()

    def exists(self) -> bool:
        pass
