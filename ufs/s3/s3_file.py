import hashlib
from io import BytesIO

from ufs.base import File
from ufs.s3.s3_common import S3Object


class S3File(S3Object, File):
    def _download(self, dst: "PosixObject"):
        self._client.download_file(Bucket=self.bucket_name, Key=self.prefix, Filename=str(dst))

    def _upload(self, src: "PosixObject"):
        self._client.upload_file(Bucket=self.bucket_name, Key=self.prefix, Filename=str(src))

    def size(self) -> int:
        try:
            response = self._client.head_object(Bucket=self.bucket_name, Key=self.prefix)
            return response['ContentLength']
        except:
            # if there is a permission error for head_object
            response = self._client.get_object(Bucket=self.bucket_name, Key=self.prefix)
            return response['ContentLength']

    def exists(self) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=self.prefix)
            return True
        except:
            # if there is a permission error for head_object
            try:
                self._client.get_object(Bucket=self.bucket_name, Key=self.prefix)
                return True
            except:
                pass
        return False

    def write_text(self, content: str, mode, *args, **kwargs):
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=self.prefix,
            Body=content.encode('urf-8')
        )

    def write_bytes(self, content: bytes, mode, encoding="utf-8", *args, **kwargs):
        self._client.put_object(
            Bucket=self.bucket_name,
            Key=self.prefix,
            Body=content
        )

    def touch(self, *args, **kwargs):
        pass

    def remove(self, dry_run: bool = False, *args, **kwargs):
        if dry_run:
            print(f'Deleting: s3://{self.bucket_name}/{self.prefix}')
            return
        self._client.delete_object(Bucket=self.bucket_name, Key=self.prefix)

    def read_text(self):
        response = self._client.get_object(Bucket=self.bucket_name, Key=self.prefix)
        return response['Body'].read().decode('utf-8')

    def read_bytes(self):
        response = self._client.get_object(Bucket=self.bucket_name, Key=self.prefix)
        return response['Body'].read()

    def checksum(self, *args, **kwargs) -> str:
        content = self.read_bytes()
        digest = hashlib.file_digest(BytesIO(content), "sha256")
        return digest.hexdigest()

    def duplicate(self, dst: "File"):
        raise NotImplementedError

    def copy_to(self, dst: "Directory"):
        raise NotImplementedError
