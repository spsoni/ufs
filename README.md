# Unified File System

[![CI](https://github.com/spsoni/ufs/actions/workflows/python-package.yml/badge.svg)](https://github.com/spsoni/ufs/actions/workflows/python-package.yml)
[![CodeQL](https://github.com/spsoni/ufs/actions/workflows/codeql.yml/badge.svg)](https://github.com/spsoni/ufs/actions/workflows/codeql.yml)
[![PyPI](https://img.shields.io/pypi/v/ufs)](https://pypi.org/project/ufs/)

A common problem: you write code against the local filesystem first, then have to make it
work with S3, which usually means duplicating the logic with `os`/`shutil` on one side and
`boto3` on the other.

`ufs` gives you one object-oriented API for both. `PosixFile` and `S3File` share the `File`
interface, and `PosixDirectory` and `S3Directory` share the `Directory` interface, so your
functions can take either kind of path.

## Installation

```bash
pip install ufs          # local filesystem only
pip install 'ufs[s3]'    # adds S3 support (boto3)
```

Requires Python 3.11+.

## Usage

```python
from ufs import FS

# The factory picks the implementation from the path.
src = FS.to_directory("/data/reports")  # PosixDirectory
dst = FS.to_directory("s3://my-bucket/reports")  # S3Directory

for f in src.list_file_objects():
    print(f, f.size(), f.checksum())

src.duplicate(dst, dir_exist_ok=True)  # upload the whole tree
dst.archive_to(FS.to_file("/tmp/reports.zip"), "zip")

note = dst.join_as_file("notes", "readme.txt")
note.write_text("hello")
assert note.read_text() == "hello"
note.copy_to(FS.to_directory("/tmp/inbox"))  # -> /tmp/inbox/readme.txt
```

Code written against the base classes works with either backend:

```python
from ufs import Directory


def newest_csvs(directory: Directory, n: int = 10) -> list[str]:
    return [p for p in directory.list_files() if p.endswith(".csv")][:n]
```

### S3 client

By default each S3 object creates `boto3.client("s3")` on first use. To control credentials,
region or endpoint, pass your own client. Objects derived from it (`join_as_file`,
`list_file_objects`, ...) reuse it:

```python
import boto3
from ufs import FS

client = boto3.client("s3", endpoint_url="http://localhost:9000")
bucket = FS.to_directory("s3://my-bucket/", s3_client=client)
```

### Behaviour notes

- Directory paths always end with `/`. Relative local paths are made absolute.
- Local writes create missing parent directories, the same as S3 where directories are implicit.
- S3 directories are logical by default: `create()` does nothing and `exists()` is true
  when there is at least one object under the prefix. Pass `keep_directories_logical=False`
  to have `create()` write a `prefix/` marker object instead.
- `APPEND` mode is not supported on S3 and raises `UnsupportedOperationError`.
- `remove(dry_run=True)` logs what would be deleted (logger `ufs.*`) and deletes nothing.
  `Directory.remove()` returns the file paths it removed.
- Archive formats: `zip`, `tar`, `gztar`, `bztar`, `xztar`. The destination's extension
  must match the format.

## Development

The project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync                      # create .venv with dev dependencies
uv run pytest                # tests (S3 is mocked with moto)
uv run ruff check . && uv run ruff format --check .
uv run mypy ufs tests
uv run pre-commit install    # optional: lint on commit
uv build                     # sdist + wheel in dist/
```

## License

MIT
