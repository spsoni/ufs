import os.path
import tempfile
from os.path import join
from uuid import uuid4

from ufs.base import Directory, File
from ufs.s3.s3_common import S3Object, delete_s3_objects


class S3Directory(S3Object, Directory):
    def size(self) -> int:
        paginator = self._client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=self.bucket_name, Prefix=self.prefx
        )
        full_size = 0
        for response in response_iterator:
            if "Contents" not in response:
                continue
            for content in response["Contents"]:
                full_size += content["Size"]
        return full_size

    def exists(self) -> bool:
        if self.keep_directories_logical:
            return True
        files = self.list_files(limit=1)
        if len(files) > 0:
            return True
        return False

    def create(self, parents: bool = True, exist_ok: bool = False, *args, **kwargs):
        if self.keep_directories_logical:
            return
        raise NotImplementedError

    def duplicate(self, dst: "Directory", dir_exist_ok: bool = False):
        from ufs.posix.posix_directory import PosixDirectory

        if isinstance(dst, PosixDirectory):
            return self._download(dst)
        elif not isinstance(dst, S3Directory):
            raise NotImplementedError

        source_prefix = self._path
        for file_path in self.list_files(recursive=True):
            _, _, source_bucket, file_path_prefix = file_path.split("/", 3)
            source_relative_prefix = file_path.replace(source_prefix, "")
            dst_file = dst.join_as_file(source_relative_prefix)
            # create missing intermediate directories on Posix FileSystem
            dst_dirname = os.path.dirname(dst_file)
            os.makedirs(dst_dirname, exist_ok=True)

            self._client.copy(
                copy_source=dict(Bucket=source_bucket, Key=file_path_prefix),
                Bucket=dst_file.bucket_name,
                Key=dst_file.prefix,
            )

    def join_as_file(self, *other) -> "File":
        from ufs.s3.s3_file import S3File

        return S3File(join(self, *other))

    def join_as_directory(self, *other) -> "Directory":
        return S3Directory(join(self, *other))

    def remove(self, missing_ok: bool = True, dry_run: bool = False, *args, **kwargs):
        objects_list = list()

        for file_path in self.list_files(recursive=True):
            _, _, _, prefix = file_path.split("/", 3)
            objects_list.append(dict(Key=prefix))
            if len(objects_list) == 1000:
                delete_s3_objects(
                    s3_client=self._client,
                    bucket_name=self.bucket_name,
                    objects_list=objects_list,
                    dry_run=dry_run,
                )
                objects_list = list()

        if objects_list:
            delete_s3_objects(
                s3_client=self._client,
                bucket_name=self.bucket_name,
                objects_list=objects_list,
                dry_run=dry_run,
            )

    def list_files(
            self, recursive: bool = True, limit: int = -1, *args, **kwargs
    ) -> list:
        # TODO: pending implementation for recursive=False
        paginator = self._client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=self.bucket_name, Prefix=self.prefx
        )
        files = list()
        counter = 0
        for response in response_iterator:
            if "Contents" not in response:
                continue
            for content in response["Contents"]:
                file_prefix = content["Key"]
                files.append(f"{self._protocol}{self.bucket_name}/{file_prefix}")
                counter += 1
                if 0 < limit <= counter:
                    break
            if 0 < limit <= counter:
                break

        return files

    def list_file_objects(
            self, recursive: bool = True, limit: int = -1, *args, **kwargs
    ) -> list:
        from ufs.s3.s3_file import S3File

        file_objects = list()
        for file_path in self.list_files(recursive, limit=limit):
            file_objects.append(S3File(file_path))
        return file_objects

    def copy_to(self, dst: "Directory", dir_exist_ok: bool = False):
        source_basename = os.path.basename(self)
        dst = dst.join_as_directory(source_basename)
        return self.duplicate(dst)

    def zip_to(self, dst: File):
        from ufs.posix.posix_directory import PosixDirectory
        from ufs.posix.posix_file import PosixFile
        from ufs.s3.s3_file import S3File

        with tempfile.TemporaryDirectory() as temp_staging:
            temp_stg = PosixDirectory(temp_staging)
            # first download source s3 directory to Posix Directory
            self._download(temp_stg)

            if isinstance(dst, PosixFile):
                temp_stg.zip_to(dst)
            elif not isinstance(dst, S3File):
                raise NotImplementedError

            # then, zip it to Posix File (temporary) first
            temp_zip_file = PosixFile(f"/tmp/{uuid4()}/{os.path.basename(dst)}")
            temp_stg.zip_to(temp_zip_file)
            # then, upload to dst S3 File
            dst._upload(temp_zip_file)

    def tar_gz_to(self, dst: File):
        from ufs.posix.posix_directory import PosixDirectory
        from ufs.posix.posix_file import PosixFile
        from ufs.s3.s3_file import S3File

        with tempfile.TemporaryDirectory() as temp_staging:
            temp_stg = PosixDirectory(temp_staging)
            # first download source s3 directory to Posix Directory
            self._download(temp_stg)

            if isinstance(dst, PosixFile):
                temp_stg.tar_gz_to(dst)
            elif not isinstance(dst, S3File):
                raise NotImplementedError

            # then, zip it to Posix File (temporary) first
            temp_tar_gz_file = PosixFile(f"/tmp/{uuid4()}/{os.path.basename(dst)}")
            temp_stg.tar_gz_to(temp_tar_gz_file)
            # then, upload to dst S3 File
            dst._upload(temp_tar_gz_file)

    def file_count(self) -> int:
        return len(self.list_files(recursive=True))

    def is_directory_path(self) -> bool:
        return True

    def _download(self, dst: "PosixObject"):
        """
        Download S3Directory into posix directory
        e.g. S3Directory = s3://bucket_name/file/path/
            with file s3://bucket_name/file/path/prefix/file1.txt
        into PosixDirectory /tmp/somewhere/
            as /tmp/somewhere/prefix/file1.txt
        outcome
        :param dst: PosixDirectory, where contents of the source directory need to be downloaded into
        :return: None
        """
        from ufs.posix.posix_directory import PosixDirectory

        dst: PosixDirectory = dst.as_directory()
        source_prefix = self._path
        for file_path in self.list_files(recursive=True):
            _, _, _, download_source_prefix = file_path.split("/", 3)
            source_relative_prefix = file_path.replace(source_prefix, "")
            dst_file = dst.join_as_file(source_relative_prefix)
            # create missing intermediate directories on Posix FileSystem
            dst_dirname = os.path.dirname(dst_file)
            os.makedirs(dst_dirname, exist_ok=True)

            self._client.download_file(
                Bucket=self.bucket_name,
                Key=download_source_prefix,
                Filename=str(dst_file),
            )

    def _upload(self, src: "PosixObject"):
        """
        Upload PosixDirectory files into S3
        e.g. PosixDirectory = /tmp/somewhere/
            with file /tmp/somewhere/prefix/file1.txt
        into S3Directory s3://bucket_name/upload_to/
            as s3://bucket_name/upload_to/prefix/file1.txt
        outcome
        :param src: PosixDirectory, contents of the source directory need to be uploaded into S3
        :return: None
        """
        from ufs.posix.posix_directory import PosixDirectory

        src: PosixDirectory = src.as_directory()
        src_prefix = str(src)
        for file_path in src.list_files(recursive=True):
            source_relative_path = file_path.replace(src_prefix, "")
            dst_prefix = join(self.prefix, source_relative_path)
            self._client.upload_file(
                Filename=file_path, Bucket=self.bucket_name, Key=dst_prefix
            )
