"""The same code exercised against both backends: the point of ufs."""

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from ufs import FS, Directory, File, PosixDirectory, S3Directory, UnsupportedOperationError

from .conftest import BUCKET


@pytest.fixture(params=["posix", "s3"])
def root(request: pytest.FixtureRequest, tmp_path: Path) -> Directory:
    """An empty directory on each backend."""
    if request.param == "posix":
        return FS.to_directory(tmp_path / "root")
    client: Any = request.getfixturevalue("s3_client")
    return FS.to_directory(f"s3://{BUCKET}/root/", s3_client=client)


def write_report(directory: Directory, rows: list[dict[str, str]]) -> File:
    """Backend-agnostic code, the kind ufs is meant for."""
    report = directory.join_as_file("reports", "2024", "sales.csv")
    with report.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["region", "total"])
        writer.writeheader()
        writer.writerows(rows)
    return report


def test_csv_round_trip(root: Directory) -> None:
    rows = [{"region": "north", "total": "10"}, {"region": "süd", "total": "20"}]
    report = write_report(root, rows)
    with report.open() as f:
        assert list(csv.DictReader(f)) == rows


def test_json_and_binary_streams(root: Directory) -> None:
    doc = root / "config.json"
    assert isinstance(doc, File)
    with doc.open("w") as f:
        json.dump({"ok": True}, f)
    with doc.open("r") as f:
        assert json.load(f) == {"ok": True}

    blob = root.join_as_file("blob.bin")
    with blob.open("wb") as f:
        f.write(b"\x00\x01")
        f.write(b"\x02")
    with blob.open("rb") as f:
        assert f.read() == b"\x00\x01\x02"


def test_failed_write_leaves_no_file_on_s3(root: Directory) -> None:
    target = root.join_as_file("partial.txt")
    with pytest.raises(RuntimeError), target.open("w") as f:
        f.write("half")
        raise RuntimeError("boom")
    if isinstance(root, S3Directory):
        assert not target.exists()


def test_append(root: Directory) -> None:
    log = root.join_as_file("log.txt")
    log.write_text("one\n")
    if isinstance(root, PosixDirectory):
        with log.open("a") as f:
            f.write("two\n")
        assert log.read_text() == "one\ntwo\n"
    else:
        with pytest.raises(UnsupportedOperationError):
            log.open("a")


@pytest.mark.parametrize("mode", ["", "rw", "rbt", "x", "r+"])
def test_invalid_open_modes(root: Directory, mode: str) -> None:
    with pytest.raises(ValueError):
        root.join_as_file("f").open(mode)  # type: ignore[call-overload]


def test_path_helpers(root: Directory) -> None:
    f = root.join_as_file("a", "b", "data.tar.gz")
    assert (f.name, f.stem, f.suffix) == ("data.tar.gz", "data.tar", ".gz")
    assert f.parent == root.join_as_directory("a", "b")
    assert f.parent.parent.parent == root
    assert root.join_as_directory("sub").name == "sub"
    assert root / "x.txt" == root.join_as_file("x.txt")
    assert root / "x/" == root.join_as_directory("x")


def test_parent_of_root_is_root(root: Directory) -> None:
    top = root.parent
    while top.parent != top:
        top = top.parent
    assert str(top) in ("/", f"s3://{BUCKET}/")


def test_glob(root: Directory) -> None:
    for name in ["a.csv", "b.txt", "2024/c.csv", "2024/q1/d.csv"]:
        root.join_as_file(name).write_text(name)

    def names(files: list[File]) -> list[str]:
        return [str(f).removeprefix(str(root)) for f in files]

    assert names(root.glob("*.csv")) == ["2024/c.csv", "2024/q1/d.csv", "a.csv"]
    assert names(root.glob("*.csv", recursive=False)) == ["a.csv"]
    assert names(root.glob("2024/*.csv")) == ["2024/c.csv", "2024/q1/d.csv"]
    assert names(root.glob("2024/q?/*")) == ["2024/q1/d.csv"]
    assert root.glob("*.parquet") == []


def test_copy_across_backends(root: Directory, tmp_path: Path) -> None:
    write_report(root, [{"region": "x", "total": "1"}])
    local = root.duplicate(FS.to_directory(tmp_path / "copy"), dir_exist_ok=True)
    assert [f.name for f in local.list_file_objects()] == ["sales.csv"]
    assert all(f.checksum() for f in local.glob("*.csv"))
