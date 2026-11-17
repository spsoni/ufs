import tarfile
import zipfile
from pathlib import Path

import pytest

from ufs import PosixDirectory, PosixFile, UnsupportedOperationError


class TestPosixFile:
    def test_text_round_trip_creates_parents(self, tmp_path: Path) -> None:
        f = PosixFile(tmp_path / "new" / "dir" / "f.txt")
        f.write_text("héllo")
        assert f.exists()
        assert f.read_text() == "héllo"
        f.write_text(" world", mode="APPEND")
        assert f.read_text() == "héllo world"
        f.write_text("over", mode="overwrite")
        assert f.read_text() == "over"

    def test_bytes_round_trip(self, tmp_path: Path) -> None:
        f = PosixFile(tmp_path / "f.bin")
        f.write_bytes(b"\x00\xff")
        f.write_bytes(b"\x01", mode="APPEND")
        assert f.read_bytes() == b"\x00\xff\x01"
        assert f.size() == 3

    def test_bad_mode(self, tmp_path: Path) -> None:
        with pytest.raises(UnsupportedOperationError):
            PosixFile(tmp_path / "f").write_text("x", mode="SIDEWAYS")

    def test_touch_and_remove(self, tmp_path: Path) -> None:
        f = PosixFile(tmp_path / "f")
        f.touch()
        assert f.exists() and f.size() == 0
        with pytest.raises(FileExistsError):
            f.touch(exist_ok=False)
        f.remove(dry_run=True)
        assert f.exists()
        f.remove()
        assert not f.exists()
        f.remove()  # missing_ok by default
        with pytest.raises(FileNotFoundError):
            f.remove(missing_ok=False)

    def test_directory_is_not_an_existing_file(self, tmp_path: Path) -> None:
        assert not PosixFile(tmp_path).exists()

    def test_duplicate_and_copy_to(self, tree: PosixDirectory, tmp_path: Path) -> None:
        src = tree.join_as_file("a.txt")
        dup = src.duplicate(PosixFile(tmp_path / "out" / "copy.txt"))
        assert dup.read_text() == "alpha"
        copied = src.copy_to(PosixDirectory(tmp_path / "dest"))
        assert copied == PosixFile(tmp_path / "dest" / "a.txt")
        assert copied.read_text() == "alpha"
        assert copied.checksum() == src.checksum()


class TestPosixDirectory:
    def test_trailing_slash(self, tmp_path: Path) -> None:
        assert str(PosixDirectory(tmp_path)).endswith("/")

    def test_listing(self, tree: PosixDirectory) -> None:
        root = str(tree)
        assert tree.list_files() == [
            root + "a.txt",
            root + "b.bin",
            root + "sub/c.txt",
            root + "sub/deep/d.txt",
        ]
        assert tree.list_files(recursive=False) == [root + "a.txt", root + "b.bin"]
        assert tree.list_files(limit=2) == [root + "a.txt", root + "b.bin"]
        assert all(isinstance(f, PosixFile) for f in tree.list_file_objects())
        assert tree.file_count() == 4
        assert tree.size() == len("alpha") + 3 + len("charlie") + len("delta")

    def test_join(self, tree: PosixDirectory) -> None:
        assert tree.join_as_file("sub", "c.txt").read_text() == "charlie"
        assert tree.join_as_file("/sub/c.txt").read_text() == "charlie"  # no escape to /
        assert tree.join_as_directory("sub").file_count() == 2

    def test_create_and_remove(self, tmp_path: Path) -> None:
        d = PosixDirectory(tmp_path / "x" / "y")
        assert not d.exists()
        d.create()
        assert d.exists()
        with pytest.raises(FileExistsError):
            d.create()
        d.join_as_file("f").touch()
        assert d.remove(dry_run=True) == [str(d) + "f"]
        assert d.exists()
        assert d.remove() == [str(d) + "f"]
        assert not d.exists()
        assert d.remove() == []
        with pytest.raises(FileNotFoundError):
            d.remove(missing_ok=False)

    def test_duplicate_and_copy_to(self, tree: PosixDirectory, tmp_path: Path) -> None:
        dup = tree.duplicate(PosixDirectory(tmp_path / "dup"))
        assert dup.file_count() == 4
        with pytest.raises(FileExistsError):
            tree.duplicate(dup)
        tree.duplicate(dup, dir_exist_ok=True)

        copied = tree.copy_to(PosixDirectory(tmp_path / "dest"))
        assert copied == PosixDirectory(tmp_path / "dest" / "root")
        assert copied.join_as_file("sub/deep/d.txt").read_text() == "delta"

    @pytest.mark.parametrize(
        ("fmt", "name"),
        [("zip", "a.zip"), ("gztar", "a.tar.gz"), ("bztar", "a.tar.bz2"), ("xztar", "a.tar.xz")],
    )
    def test_archive(self, tree: PosixDirectory, tmp_path: Path, fmt: str, name: str) -> None:
        dst = PosixFile(tmp_path / "archives" / name)
        tree.archive_to(dst, fmt)  # type: ignore[arg-type]
        assert dst.exists()
        if fmt == "zip":
            with zipfile.ZipFile(dst) as zf:
                names = zf.namelist()
        else:
            with tarfile.open(dst) as tf:
                names = tf.getnames()
        assert any(n.endswith("sub/deep/d.txt") for n in names)
