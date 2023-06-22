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
