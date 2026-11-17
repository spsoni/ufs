import hashlib
import tarfile
from pathlib import Path
from typing import Any

import pytest

from ufs import (
    FileSystemException,
    PosixDirectory,
    PosixFile,
    S3Directory,
    S3File,
    UnsupportedOperationError,
)
from ufs.s3 import s3_common

from .conftest import BUCKET


def s3file(client: Any, key: str) -> S3File:
    return S3File(f"s3://{BUCKET}/{key}", s3_client=client)


def s3dir(client: Any, key: str) -> S3Directory:
    return S3Directory(f"s3://{BUCKET}/{key}", s3_client=client)


@pytest.fixture
def s3_tree(s3_client: Any, tree: PosixDirectory) -> S3Directory:
    """The local ``tree`` fixture uploaded to s3://BUCKET/data/."""
    return tree.duplicate(s3dir(s3_client, "data/"))  # type: ignore[return-value]


class TestS3File:
    def test_round_trip(self, s3_client: Any) -> None:
        f = s3file(s3_client, "a/b.txt")
        assert (f.bucket_name, f.prefix) == (BUCKET, "a/b.txt")
        assert not f.exists()
        f.write_text("héllo")
        assert f.exists()
        assert f.read_text() == "héllo"
        assert f.size() == len("héllo".encode())
        assert f.checksum() == hashlib.sha256("héllo".encode()).hexdigest()
        f.write_bytes(b"\x00", mode="OVERWRITE")
        assert f.read_bytes() == b"\x00"

    def test_append_is_unsupported(self, s3_client: Any) -> None:
        with pytest.raises(UnsupportedOperationError):
            s3file(s3_client, "x").write_text("x", mode="APPEND")
        with pytest.raises(UnsupportedOperationError):
            s3file(s3_client, "x").write_text("x", mode="READ")

    def test_touch_and_remove(self, s3_client: Any) -> None:
        f = s3file(s3_client, "t")
        f.touch()
        assert f.exists() and f.size() == 0
        f.write_text("keep")
        f.touch()
        assert f.read_text() == "keep"
        with pytest.raises(FileExistsError):
            f.touch(exist_ok=False)
        f.remove(dry_run=True)
        assert f.exists()
        f.remove()
        assert not f.exists()
        f.remove()
        with pytest.raises(FileNotFoundError):
            f.remove(missing_ok=False)

    def test_copy_between_filesystems(self, s3_client: Any, tmp_path: Path) -> None:
        local = PosixFile(tmp_path / "src.txt")
        local.write_text("payload")

        remote = local.duplicate(s3file(s3_client, "up/src.txt"))
        assert remote.read_text() == "payload"

        remote_copy = remote.copy_to(s3dir(s3_client, "other/"))
        assert remote_copy == s3file(s3_client, "other/src.txt")
        assert remote_copy.read_text() == "payload"

        back = remote_copy.duplicate(PosixFile(tmp_path / "down" / "back.txt"))
        assert back.read_text() == "payload"

    def test_client_propagates(self, s3_client: Any) -> None:
        d = s3dir(s3_client, "p/")
        derived = [
            d.join_as_file("x"),
            d.join_as_directory("y").as_file(),
            d.parent,
            d / "z.txt",
        ]
        for obj in derived:
            assert isinstance(obj, (S3File, S3Directory))
            assert obj.client is s3_client

    def test_open_append_is_unsupported(self, s3_client: Any) -> None:
        with pytest.raises(UnsupportedOperationError):
            s3file(s3_client, "x").open("a")

    def test_open_streams_large_objects(self, s3_client: Any) -> None:
        payload = bytes(range(256)) * 20_000  # ~5 MB, spans several read chunks
        f = s3file(s3_client, "big.bin")
        with f.open("wb") as out:
            for i in range(0, len(payload), 100_000):
                out.write(payload[i : i + 100_000])
        with f.open("rb") as src:
            assert src.read(10) == payload[:10]
            assert src.read() == payload[10:]


class TestS3Directory:
    def test_listing(self, s3_tree: S3Directory) -> None:
        base = f"s3://{BUCKET}/data/"
        assert s3_tree.list_files() == [
            base + "a.txt",
            base + "b.bin",
            base + "sub/c.txt",
            base + "sub/deep/d.txt",
        ]
        assert s3_tree.list_files(recursive=False) == [base + "a.txt", base + "b.bin"]
        assert s3_tree.list_files(limit=1) == [base + "a.txt"]
        assert all(isinstance(f, S3File) for f in s3_tree.list_file_objects())
        assert s3_tree.file_count() == 4
        assert s3_tree.size() == len("alpha") + 3 + len("charlie") + len("delta")

    def test_prefix_does_not_match_siblings(self, s3_client: Any, s3_tree: S3Directory) -> None:
        s3file(s3_client, "database.txt").write_text("not in data/")
        assert s3dir(s3_client, "data").file_count() == 4

    def test_exists_and_create(self, s3_client: Any, s3_tree: S3Directory) -> None:
        assert s3_tree.exists()
        empty = s3dir(s3_client, "empty/")
        assert not empty.exists()
        empty.create()  # logical: no-op
        assert not empty.exists()

        physical = S3Directory(
            f"s3://{BUCKET}/phys/", s3_client=s3_client, keep_directories_logical=False
        )
        physical.create()
        assert physical.exists()
        assert physical.list_files() == []  # marker is not a file
        with pytest.raises(FileExistsError):
            physical.create()
        physical.create(exist_ok=True)
        assert physical.remove() == []
        assert not physical.exists()

    def test_remove(self, s3_client: Any, s3_tree: S3Directory) -> None:
        assert len(s3_tree.remove(dry_run=True)) == 4
        assert s3_tree.file_count() == 4
        assert len(s3_tree.remove()) == 4
        assert not s3_tree.exists()
        assert s3_tree.remove() == []
        with pytest.raises(FileNotFoundError):
            s3_tree.remove(missing_ok=False)

    def test_remove_batches(
        self, s3_client: Any, monkeypatch: pytest.MonkeyPatch, s3_tree: S3Directory
    ) -> None:
        monkeypatch.setattr(s3_common, "DELETE_BATCH_SIZE", 3)
        assert len(s3_tree.remove()) == 4
        assert s3_tree.file_count() == 0

    def test_download_and_copy(self, s3_client: Any, s3_tree: S3Directory, tmp_path: Path) -> None:
        local = s3_tree.duplicate(PosixDirectory(tmp_path / "dl"))
        assert local.join_as_file("sub/deep/d.txt").read_text() == "delta"
        with pytest.raises(FileExistsError):
            s3_tree.duplicate(local)

        copied = s3_tree.copy_to(s3dir(s3_client, "backup/"))
        assert copied == s3dir(s3_client, "backup/data/")
        assert copied.join_as_file("sub/c.txt").read_text() == "charlie"

    def test_archive_to_posix_and_s3(
        self, s3_client: Any, s3_tree: S3Directory, tree: PosixDirectory, tmp_path: Path
    ) -> None:
        local_archive = PosixFile(tmp_path / "out.tar.gz")
        s3_tree.archive_to(local_archive, "gztar")
        with tarfile.open(local_archive) as tf:
            assert any(n.endswith("sub/deep/d.txt") for n in tf.getnames())

        remote_archive = s3file(s3_client, "archives/out.zip")
        s3_tree.archive_to(remote_archive, "zip")
        assert remote_archive.exists()

        tree.archive_to(s3file(s3_client, "archives/local.tar.gz"), "gztar")
        assert s3file(s3_client, "archives/local.tar.gz").size() > 0


def test_delete_errors_raise() -> None:
    class FakeClient:
        def delete_objects(self, **_: Any) -> dict[str, Any]:
            return {"Errors": [{"Key": "k", "Code": "AccessDenied"}]}

    with pytest.raises(FileSystemException):
        s3_common.delete_s3_objects(FakeClient(), "b", ["k"])
