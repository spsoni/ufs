# Paths

Every `ufs` object wraps a path string and behaves like one where it makes sense.

## Creating objects

| Path | `FS.to_file` | `FS.to_directory` |
| --- | --- | --- |
| `/abs/path`, `relative/path` | `PosixFile` | `PosixDirectory` |
| `s3://bucket/key`, `s3a://bucket/key` | `S3File` | `S3Directory` |

- Relative local paths are made absolute against the current working directory.
- Directory paths always end with `/`, so `FS.to_directory("/tmp/x")` is `/tmp/x/`.
- An `S3File` needs a key: `s3://bucket` and `s3://bucket/` are rejected with
  `InvalidPathError`.
- `s3a://` paths are rewritten to `s3://` by default. Pass `protocol="s3a://"` to keep them.

## Path-like behaviour

```python
import os
from ufs import FS

f = FS.to_file("/data/2024/sales.tar.gz")

str(f)          # '/data/2024/sales.tar.gz'
os.fspath(f)    # same: works with open(), shutil, pandas, ...
f.name          # 'sales.tar.gz'
f.stem          # 'sales.tar'
f.suffix        # '.gz'
f.parent        # PosixDirectory('/data/2024/')
f.endswith(".gz")
```

Objects compare and hash by type and path, so you can put them in sets and dicts.
`PosixFile("/a") != PosixDirectory("/a")`.

## Joining

```python
d = FS.to_directory("s3://bucket/data")

d.join_as_file("2024", "sales.csv")    # S3File('s3://bucket/data/2024/sales.csv')
d.join_as_directory("2024")            # S3Directory('s3://bucket/data/2024/')
d / "sales.csv"                        # a File
d / "2024/"                            # a Directory (trailing slash)
```

Leading slashes in joined parts are stripped, so a part can never escape the directory:
`d.join_as_file("/etc/passwd")` is `s3://bucket/data/etc/passwd`.

## Converting

`as_file()` and `as_directory()` switch between the two views of the same path, keeping
the backend and any S3 options:

```python
FS.to_file("/a/b").as_directory()   # PosixDirectory('/a/b/')
```
