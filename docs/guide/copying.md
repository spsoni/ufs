# Copying and archiving

## Files

| Method | Meaning |
| --- | --- |
| `src.duplicate(dst_file)` | copy to exactly `dst_file` |
| `src.copy_to(dst_dir)` | copy into `dst_dir`, keeping the name |

Both work across backends and return the destination:

```python
local = FS.to_file("/tmp/report.pdf")
remote = local.copy_to(FS.to_directory("s3://bucket/reports"))   # upload
backup = remote.duplicate(FS.to_file("s3://backup/report.pdf"))  # server-side S3 copy
remote.duplicate(FS.to_file("/tmp/again.pdf"))                   # download
```

S3→S3 copies happen server-side; the data never passes through your machine.

## Directories

| Method | Meaning |
| --- | --- |
| `src.duplicate(dst_dir)` | copy the *contents* of `src` into `dst_dir` |
| `src.copy_to(dst_dir)` | copy `src` itself into `dst_dir` (`dst_dir/<name>/...`) |

```python
src = FS.to_directory("/srv/site")
src.duplicate(FS.to_directory("s3://bucket/site"))   # s3://bucket/site/index.html
src.copy_to(FS.to_directory("s3://bucket/sites"))    # s3://bucket/sites/site/index.html
```

When the destination is local and already exists, pass `dir_exist_ok=True` to merge into it.

## Archives

```python
d = FS.to_directory("s3://bucket/logs/2024")
d.archive_to(FS.to_file("/tmp/logs.tar.gz"), "gztar")
d.archive_to(FS.to_file("s3://bucket/archive/logs-2024.zip"), "zip")
```

| Format | Extension |
| --- | --- |
| `zip` | `.zip` |
| `tar` | `.tar` |
| `gztar` | `.tar.gz` |
| `bztar` | `.tar.bz2` |
| `xztar` | `.tar.xz` |

The destination's extension must match the format (`InvalidPathError` otherwise). S3 sources
and destinations are staged through a temporary local directory that is cleaned up afterwards.
