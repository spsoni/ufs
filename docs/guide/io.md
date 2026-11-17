# Reading and writing

## Whole-file helpers

```python
f.write_text("héllo")                 # utf-8 by default
f.write_bytes(b"\x00\x01")
f.read_text()
f.read_bytes()
f.touch()                             # create if missing; never truncates
f.size()                              # bytes
f.exists()
f.checksum()                          # sha256 hex digest, streamed
f.checksum("md5")                     # any hashlib algorithm
f.remove()                            # missing_ok=True by default
```

`write_text`/`write_bytes` take a `mode`: `"WRITE"` (default) or `"OVERWRITE"` replace the
file, and `"APPEND"` adds to it (local files only).

## Streaming with `open()`

`open()` mirrors the built-in function and returns a real file object:

```python
with f.open() as fh:                  # "r": text, utf-8
    for line in fh:
        ...

with f.open("wb") as fh:              # binary write
    fh.write(chunk)

with f.open("w", newline="") as fh:   # e.g. for the csv module
    csv.writer(fh).writerows(rows)
```

Supported modes are `r`, `w` and `a`, optionally with `b` (binary) or `t` (text, the
default). Text mode accepts `encoding`, `errors` and `newline`.

Because the result is a standard stream, third-party libraries work directly:

```python
import pandas as pd

with FS.to_file("s3://bucket/data.csv").open() as fh:
    df = pd.read_csv(fh)
```

### On S3

- **Reads** stream from the object in 1 MiB chunks, so large objects are never fully loaded
  into memory. The stream is forward-only (not seekable).
- **Writes** are buffered in memory up to 8 MiB, then spill to a temporary file. The object
  is uploaded when the file is closed, using multipart upload for large files.
- **Atomic on failure:** if the `with` block raises, nothing is uploaded and any existing
  object is left untouched.
- **Append** (`"a"`) is not supported, because S3 objects are immutable. It raises
  `UnsupportedOperationError`.

## Local files

Writing to a local file creates any missing parent directories, just as S3 doesn't need a
"directory" to exist first. This keeps code portable between the two backends.
