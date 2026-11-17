# Directories

## Listing

```python
d = FS.to_directory("s3://bucket/data")

d.list_files()                        # ['s3://bucket/data/a.csv', 's3://bucket/data/2024/b.csv', ...]
d.list_files(recursive=False)         # direct children only
d.list_files(limit=100)               # first 100 (stops early on S3)
d.list_file_objects()                 # same, as File objects
d.file_count()
d.size()                              # total bytes
```

Results are sorted by path.

## Globbing

`glob()` matches the path *relative to the directory* using shell-style wildcards
(`*`, `?`, `[abc]`):

```python
d.glob("*.csv")                       # CSV files at any depth
d.glob("*.csv", recursive=False)      # top level only
d.glob("2024/*.csv")                  # under 2024/
d.glob("2024/q?/*")                   # 2024/q1/..., 2024/q2/...
```

!!! note
    As in Python's `fnmatch`, `*` also matches `/`, so `"*.csv"` finds files in sub-directories.

## Creating and existence

```python
local = FS.to_directory("/tmp/out")
local.create()                        # parents=True, exist_ok=False
local.exists()
```

S3 has no real directories. By default `S3Directory.create()` does nothing and `exists()`
is true when at least one object has the prefix. See
[Configuring S3](s3.md#logical-vs-marker-directories) for the alternative.

## Deleting

```python
d.remove(dry_run=True)    # log what would be deleted, delete nothing
removed = d.remove()      # list of removed file paths
```

Missing directories are ignored unless you pass `missing_ok=False`. On S3, deletes are sent
in batches of 1,000 keys, and any per-key failure raises `FileSystemException`.

Dry-run output goes to the standard `logging` module (loggers under `ufs.`), so enable it
with, for example, `logging.basicConfig(level=logging.INFO)`.
