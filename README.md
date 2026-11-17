<div align="center">

# ufs · Unified File System

**One object-oriented API for local and S3 files.**<br>
Write your file-handling code once and run it against `/local/paths` or `s3://bucket/keys`.

[![PyPI](https://img.shields.io/pypi/v/ufs?color=blue)](https://pypi.org/project/ufs/)
[![Python](https://img.shields.io/pypi/pyversions/ufs)](https://pypi.org/project/ufs/)
[![CI](https://github.com/spsoni/ufs/actions/workflows/python-package.yml/badge.svg)](https://github.com/spsoni/ufs/actions/workflows/python-package.yml)
[![Docs](https://github.com/spsoni/ufs/actions/workflows/docs.yml/badge.svg)](https://spsoni.github.io/ufs/)
[![CodeQL](https://github.com/spsoni/ufs/actions/workflows/codeql.yml/badge.svg)](https://github.com/spsoni/ufs/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[Documentation](https://spsoni.github.io/ufs/) ·
[Getting started](https://spsoni.github.io/ufs/getting-started/) ·
[API reference](https://spsoni.github.io/ufs/api/) ·
[Changelog](CHANGELOG.md)

</div>

---

## Why ufs?

Code that starts out on the local filesystem usually ends up needing to work with S3 too.
That tends to produce two code paths, one built on `os`/`shutil` and one on `boto3`, which
then drift apart. `ufs` gives you `File` and `Directory` abstractions with a local
implementation and an S3 implementation, so your functions can accept either:

```python
import csv
from ufs import FS, Directory


def export(rows: list[dict[str, str]], out: Directory) -> None:
    with out.join_as_file("export.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


export(rows, FS.to_directory("/tmp/out"))         # during development
export(rows, FS.to_directory("s3://bucket/out"))  # in production, with no code changes
```

## Features

- **Same API on both backends:** `PosixFile`/`S3File` and `PosixDirectory`/`S3Directory`
  share one interface.
- **Streaming `open()`:** works with `csv`, `json`, pandas and anything else that takes a
  file object. S3 reads stream in chunks, and S3 writes upload on close.
- **Path ergonomics:** `/` joins, `parent`, `name`, `stem`, `suffix` and `glob()`.
- **Copying in every direction:** local↔S3 and within each backend, for single files or
  whole trees. S3→S3 copies happen server-side.
- **Archiving** to `zip`, `tar`, `tar.gz`, `tar.bz2` or `tar.xz`, locally or straight to S3.
- **Safe by default:** `dry_run` deletes, no partial uploads when a write fails, and a clear
  exception hierarchy.
- **Typed and tested:** ships `py.typed`, passes strict mypy, and is tested against moto on
  Python 3.11–3.14.

## Installation

```bash
pip install ufs          # local filesystem only, no dependencies
pip install 'ufs[s3]'    # adds S3 support via boto3
```

## Quick tour

```python
from ufs import FS

data = FS.to_directory("s3://my-bucket/data")  # or "/srv/data"

# Read and write
report = data.join_as_file("2024", "report.txt")  # or: data / "2024/report.txt"
report.write_text("hello")
report.read_text()                              # 'hello'

with data.join_as_file("big.bin").open("wb") as f:  # streamed upload
    f.write(b"...")

# Explore
data.list_files(recursive=False)
data.glob("2024/*.csv")
report.name, report.suffix, report.parent      # ('report.txt', '.txt', S3Directory('s3://my-bucket/data/2024/'))

# Copy and archive across backends
report.copy_to(FS.to_directory("/tmp/inbox"))   # download
data.duplicate(FS.to_directory("s3://backup/data"))
data.archive_to(FS.to_file("/tmp/data.tar.gz"), "gztar")

# Clean up safely
data.remove(dry_run=True)                      # logs what would be deleted
```

To use specific credentials, a region, or an S3-compatible service such as MinIO or R2,
pass your own client:

```python
import boto3

client = boto3.client("s3", endpoint_url="http://localhost:9000")
data = FS.to_directory("s3://my-bucket/data", s3_client=client)
```

See the [user guide](https://spsoni.github.io/ufs/guide/paths/) for every feature.

## API at a glance

| | Local | S3 |
| --- | --- | --- |
| File | `PosixFile` | `S3File` |
| Directory | `PosixDirectory` | `S3Directory` |
| Build from any path | `FS.to_file(path)`, `FS.to_directory(path)` | ← same |
| Streaming | `open("r" / "w" / "a" / "rb" / "wb" / "ab")` | no `a`/`ab` (objects are immutable) |
| Whole file | `read_text`, `read_bytes`, `write_text`, `write_bytes`, `touch`, `remove` | ← same |
| Metadata | `exists`, `size`, `checksum`, `name`, `stem`, `suffix`, `parent` | ← same |
| Directories | `list_files`, `list_file_objects`, `glob`, `file_count`, `create`, `remove` | ← same |
| Transfer | `duplicate`, `copy_to`, `archive_to` | ← same, across backends |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup
(uv, pytest, ruff, mypy, mkdocs). To report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Sury Soni
