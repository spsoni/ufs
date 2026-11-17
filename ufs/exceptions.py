class FileSystemException(Exception):
    """Base class for all errors raised by ufs."""


class InvalidPathError(FileSystemException, ValueError):
    """The path is not valid for the requested filesystem object."""


class UnsupportedOperationError(FileSystemException, NotImplementedError):
    """The operation is not supported by this filesystem."""
