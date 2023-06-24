from abc import ABC, abstractmethod

from ufs.base import FileSystemObject


class S3Object(FileSystemObject, ABC):
    def __init__(
            self,
            path,
            s3_client=None,
            protocol: str = "s3://",
            keep_directories_logical: bool = True,
            *args,
            **kwargs,
    ):
        if protocol == "s3://":
            if path.startswith("s3a://"):
                path = path.replace("s3a://", "s3://")
        elif protocol == "s3a://":
            if path.startswith("s3://"):
                path = path.replace("s3://", "s3a://")

        super().__init__(path, *args, **kwargs)

        self._client = s3_client
        self._protocol = protocol
        self.keep_directories_logical = keep_directories_logical

        _, _, bucket_name, prefix = self._path.split("/", 3)

        self.bucket_name = bucket_name
        self.prefix = prefix

    def _validate_path(self, path) -> bool:
        return path.startswith(self._protocol)

    @abstractmethod
    def _download(self, dst: "PosixObject"):
        raise NotImplementedError

    @abstractmethod
    def _upload(self, src: "PosixObject"):
        raise NotImplementedError

    def as_file(self) -> "File":
        from ufs.s3.s3_file import S3File

        return S3File(self._path)

    def as_directory(self) -> "Directory":
        from ufs.s3.s3_directory import S3Directory

        return S3Directory(self._path)


def delete_s3_objects(
        s3_client, bucket_name, objects_list: list, dry_run: bool = False
):
    if dry_run:
        for prefix in objects_list:
            print(f"Deleting: s3://{bucket_name}/{prefix}")
        return

    s3_client.delete_s3_objects(
        Bucket=bucket_name,
        Delete=dict(Objects=objects_list, Quiet=True),
    )
