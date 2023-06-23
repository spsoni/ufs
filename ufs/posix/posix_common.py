import os


def convert_mode(mode: str, format: str) -> str:
    mode = mode.upper()
    m = "r"
    if mode == "READ":
        m = "r"
    elif mode in ("WRITE", "OVERWRITE"):
        m = "w"
    elif mode == "APPEND":
        m = "a"
    else:
        raise RuntimeError(f"Un-supported mode = {mode}")

    if format == "bytes":
        return f"{m}b"
    elif format == "text":
        return m

    raise RuntimeError(f"Invalid format: {format}")


def file_counter(path: str) -> int:
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += 1
            elif entry.is_dir():
                total += file_counter(entry.path)
    return total


def get_files_list(path: str, recursive: bool = True) -> list:
    files = list()
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                files.append(str(entry.path))
            elif entry.is_dir() and recursive:
                files.extend(get_files_list(str(entry.path), recursive))

    return files


def get_dir_size(path: str):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total
