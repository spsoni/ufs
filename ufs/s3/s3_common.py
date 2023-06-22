from ufs.base import FileSystemObject


class S3Object(FileSystemObject):
    def __init__(self, path, s3_client=None, protocol: str = "s3://", *args, **kwargs):
        if protocol == "s3://":
            if path.startswith("s3a://"):
                path = path.replace("s3a://", "s3://")
        elif protocol == "s3a://":
            if path.startswith("s3://"):
                path = path.replace("s3://", "s3a://")

        super().__init__(path, *args, **kwargs)

        self._client = s3_client
        self._protocol = protocol

    def _validate_path(self, path) -> bool:
        return path.startswith(self._protocol)

    def size(self) -> int:
        pass

    def exists(self) -> bool:
        pass
