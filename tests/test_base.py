import hashlib
import os

import pytest

from ufs import (
    FS,
    FileSystem,
    InvalidPathError,
    PosixDirectory,
    PosixFile,
    S3Directory,
    S3File,
    UnsupportedOperationError,
    __version__,
)
from ufs.base import archive_base_name


def test_version_is_set() -> None:
    assert __version__


@pytest.mark.parametrize(
    ("path", "cls"),
    [
        ("/tmp/x.txt", PosixFile),
        ("  /tmp/x.txt  ", PosixFile),
        ("relative/x.txt", PosixFile),
        ("s3://bucket/x.txt", S3File),
        ("s3a://bucket/x.txt", S3File),
    ],
)
def test_to_file_dispatch(path: str, cls: type) -> None:
    assert isinstance(FileSystem.to_file(path), cls)


@pytest.mark.parametrize(
    ("path", "cls"),
    [("/tmp/x", PosixDirectory), ("s3://bucket/x", S3Directory), ("s3://bucket", S3Directory)],
)
def test_to_directory_dispatch(path: str, cls: type) -> None:
    d = FS.to_directory(path)
    assert isinstance(d, cls)
    assert str(d).endswith("/")


def test_relative_posix_paths_become_absolute() -> None:
    assert str(PosixFile("x.txt")) == os.path.join(os.getcwd(), "x.txt")


def test_pathlike_and_equality() -> None:
    f = PosixFile("/tmp/x.txt")
    assert os.fspath(f) == "/tmp/x.txt"
    assert f == PosixFile("/tmp/x.txt")
    assert f != PosixDirectory("/tmp/x.txt")
    assert len({f, PosixFile("/tmp/x.txt")}) == 1
    assert repr(f) == "PosixFile('/tmp/x.txt')"
    assert f.startswith("/tmp") and f.endswith(".txt")


def test_basename_ignores_trailing_slash() -> None:
    assert PosixDirectory("/a/b/").basename() == "b"
    assert S3Directory("s3://bucket/a/b/").basename() == "b"
    assert PosixFile("/a/b.txt").basename() == "b.txt"


def test_type_predicates() -> None:
    assert PosixFile("/a").is_file_path() and not PosixFile("/a").is_directory_path()
    assert PosixDirectory("/a").is_directory_path() and not PosixDirectory("/a").is_file_path()


@pytest.mark.parametrize("bad", ["s3://", "s3://bucket", "s3://bucket/", "gs://bucket/x"])
def test_invalid_s3_file_paths(bad: str) -> None:
    with pytest.raises(InvalidPathError):
        S3File(bad)


def test_invalid_s3_protocol() -> None:
    with pytest.raises(InvalidPathError):
        S3File("s3://bucket/x", protocol="gs://")


def test_s3a_protocol_rewrite() -> None:
    assert str(S3File("s3a://b/k")) == "s3://b/k"
    f = S3File("s3://b/k", protocol="s3a://")
    assert str(f) == "s3a://b/k"
    assert (f.bucket_name, f.prefix) == ("b", "k")


def test_as_file_as_directory_round_trip() -> None:
    assert PosixFile("/a/b").as_directory() == PosixDirectory("/a/b/")
    assert PosixDirectory("/a/b/").as_file() == PosixFile("/a/b")
    assert S3File("s3://b/k").as_directory() == S3Directory("s3://b/k/")
    assert S3Directory("s3://b/k/").as_file() == S3File("s3://b/k")


def test_archive_base_name() -> None:
    assert archive_base_name(PosixFile("/x/out.tar.gz"), "gztar") == "/x/out"
    with pytest.raises(InvalidPathError):
        archive_base_name(PosixFile("/x/out.zip"), "gztar")
    with pytest.raises(UnsupportedOperationError):
        archive_base_name(PosixFile("/x/out.rar"), "rar")


def test_checksum_algorithms(tmp_path: os.PathLike[str]) -> None:
    f = PosixFile(os.path.join(tmp_path, "f"))
    f.write_bytes(b"hello")
    assert f.checksum() == hashlib.sha256(b"hello").hexdigest()
    assert f.checksum("md5") == hashlib.md5(b"hello").hexdigest()
