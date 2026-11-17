# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - Unreleased

### Changed
- **Breaking:** requires Python 3.11+ (3.8–3.10 are end-of-life).
- **Breaking:** `boto3` is now an optional extra: `pip install 'ufs[s3]'`.
- Packaging moved from Poetry to PEP 621 metadata, the hatchling build backend and uv.
- `FileSystem.to_file`/`to_directory` accept `os.PathLike`, treat anything not starting
  with `s3://`/`s3a://` as a local path, and take an optional `s3_client`.
- Relative local paths are resolved to absolute paths.
- Local writes create missing parent directories.
- `dry_run` deletes log through `logging` instead of `print`, and `Directory.remove()`
  returns the removed paths.
- `S3Directory.exists()` checks for objects under the prefix instead of always returning true.
- Invalid paths raise `InvalidPathError`, and unsupported operations raise
  `UnsupportedOperationError`. Both subclass `FileSystemException`.
- `write_text`/`write_bytes` default to `mode="WRITE"`. `checksum()` takes an `algorithm`
  and streams the contents.

### Added
- `File.open()` for streaming reads and writes on both backends, compatible with `csv`,
  `json`, pandas and so on. S3 writes upload on close and are discarded if the block raises.
- Path helpers: `name`, `parent`, `stem`, `suffix`, and `/` on directories.
- `Directory.glob(pattern)`.
- A documentation site (MkDocs Material + mkdocstrings) with a user guide and API reference,
  plus `CONTRIBUTING.md`.
- Copying files and directories in all four directions: local↔S3 and within each backend.
- `Directory.archive_to()`, plus the `tar`, `bztar` and `xztar` archive formats.
- `S3Directory.list_files(recursive=False)`.
- `__eq__`, `__hash__` and `__repr__` on all path objects, plus a `py.typed` marker.
- A test suite (pytest + moto), ruff, mypy (strict), pre-commit, Dependabot, and CI on
  Python 3.11–3.14.

### Fixed
- `PosixFile` could not be instantiated because `as_file`/`as_directory` were missing.
- `PosixDirectory.remove()` called `unlink()` on a directory.
- The `prefx` typo in `S3Directory.size()`/`list_files()`.
- The `"urf-8"` typo in `S3File.write_text()`.
- The non-existent `delete_s3_objects` boto3 call, now `delete_objects` with error checking.
- An S3 client was never created when none was passed.
- `copy_to()` on directories with a trailing slash used an empty basename.
- An S3 prefix without a trailing `/` matched sibling keys (`data` matched `database.txt`).
- Wrong `CopySource` argument in S3-to-S3 copies.
- The broken `S3Directory.archive_to_posix()` and `tar_gz_to()` (removed; use `archive_to`).
- `FileSystem.to_directory_prefix()` imported modules that did not exist (removed).
- The `limit` handling in local file listing.
- Bare `except:` clauses that hid real S3 errors.

## [0.1.0]

- Initial release.
