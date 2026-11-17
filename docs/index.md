# ufs — Unified File System

**One object-oriented API for local and S3 files.** Write your file-handling code once and
run it against `/local/paths` or `s3://bucket/keys` without changing a line.

```python
from ufs import FS

data = FS.to_directory("s3://my-bucket/data")  # or "/srv/data"

with data.join_as_file("report.csv").open("w") as f:
    f.write("region,total\nnorth,10\n")

for csv_file in data.glob("*.csv"):
    print(csv_file.name, csv_file.size(), csv_file.checksum())
```

## Why ufs?

Code that starts out on the local filesystem usually ends up needing to work with S3 too.
That tends to produce two code paths, one built on `os`/`shutil` and one on `boto3`, which
then drift apart. `ufs` gives you `File` and `Directory` abstractions with a local
implementation and an S3 implementation, so your functions can accept either.

## Features

- **Same API on both backends:** `PosixFile`/`S3File` and `PosixDirectory`/`S3Directory`.
- **Streaming `open()`** that works with `csv`, `json`, pandas and anything else expecting a
  file object.
- **Path ergonomics:** `/` joins, `parent`, `name`, `stem`, `suffix`, `glob()`.
- **Copying in every direction:** local→local, local→S3, S3→local, S3→S3, for files or whole
  directory trees.
- **Archiving** to `zip`, `tar`, `tar.gz`, `tar.bz2` or `tar.xz`, locally or straight to S3.
- **Safe defaults:** `dry_run` deletes, no partial uploads when a write fails, and errors
  you can catch.
- **Typed** (`py.typed`, checked with strict mypy) and tested against moto on Python 3.11–3.14.

## Next steps

- [Getting started](getting-started.md): install and do something useful in two minutes.
- [User guide](guide/paths.md): every feature, explained with examples.
- [API reference](api.md): generated from the source.
