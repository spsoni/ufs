# API reference

All public names are importable from the top-level package: `from ufs import ...`.

## Factory

::: ufs.FileSystem

## Interfaces

Type your code against these to accept any backend.

::: ufs.File

::: ufs.Directory

## Local filesystem

::: ufs.PosixFile
    options:
      inherited_members: false

::: ufs.PosixDirectory
    options:
      inherited_members: false

## Amazon S3

`S3File` and `S3Directory` take the constructor options documented on their shared base class:

::: ufs.s3.s3_common.S3Object
    options:
      inherited_members: false
      members: [client]

::: ufs.S3File
    options:
      inherited_members: false

::: ufs.S3Directory
    options:
      inherited_members: false

## Exceptions

::: ufs.FileSystemException

::: ufs.InvalidPathError

::: ufs.UnsupportedOperationError
