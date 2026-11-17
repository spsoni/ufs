# Getting started

## Installation

```bash
pip install ufs          # local filesystem only, no dependencies
pip install 'ufs[s3]'    # adds S3 support via boto3
```

`ufs` requires Python 3.11 or newer.

## Your first paths

`FS` (short for `FileSystem`) builds the right object from a path string:

```python
from ufs import FS

local = FS.to_file("/tmp/hello.txt")              # PosixFile
remote = FS.to_file("s3://my-bucket/hello.txt")   # S3File
folder = FS.to_directory("s3://my-bucket/logs")   # S3Directory, path becomes ".../logs/"
```

You can also build objects directly with `PosixFile`, `PosixDirectory`, `S3File` and
`S3Directory`.

## Read and write

```python
local.write_text("hello")
local.duplicate(remote)            # upload
assert remote.read_text() == "hello"

with remote.open("w") as f:        # streamed, uploaded when the block exits
    f.write("line 1\n")
```

## Write backend-agnostic code

Type your functions against the base classes and they accept both backends:

```python
import csv
from ufs import Directory, FS


def export(rows: list[dict[str, str]], out: Directory) -> None:
    with out.join_as_file("export.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


export(rows, FS.to_directory("/tmp/out"))            # during development
export(rows, FS.to_directory("s3://bucket/out"))     # in production
```

## S3 credentials

By default `ufs` calls `boto3.client("s3")`, which uses the standard AWS credential chain
(environment variables, `~/.aws`, instance roles, ...). To use a specific profile, region or
an S3-compatible endpoint, see [Configuring S3](guide/s3.md).
