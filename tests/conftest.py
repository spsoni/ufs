from collections.abc import Iterator
from pathlib import Path
from typing import Any

import boto3
import pytest
from moto import mock_aws

from ufs import PosixDirectory

BUCKET = "ufs-test-bucket"


@pytest.fixture
def s3_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    for var, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
    }.items():
        monkeypatch.setenv(var, value)
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client


@pytest.fixture
def tree(tmp_path: Path) -> PosixDirectory:
    """A small local directory tree::

    root/a.txt, root/b.bin, root/sub/c.txt, root/sub/deep/d.txt
    """
    root = tmp_path / "root"
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "a.txt").write_text("alpha")
    (root / "b.bin").write_bytes(b"\x00\x01\x02")
    (root / "sub" / "c.txt").write_text("charlie")
    (root / "sub" / "deep" / "d.txt").write_text("delta")
    return PosixDirectory(root)
