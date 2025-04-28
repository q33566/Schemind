from pathlib import Path


def is_in_extenstions(path: Path, extensions: list = None) -> bool:
    """
    Check if the path extension is in the list of extensions.

    Args:
        path (Path): The path to check.
        extensions (list): The list of extensions to check against.

    Returns:
        bool: True if the path extension is in the list of extensions, False otherwise.
    """
    supported_extensions = [".txt", ".csv", ".json", ".xml"]
    if extensions is None:
        extensions = supported_extensions
    if not isinstance(extensions, list):
        raise TypeError("extensions must be a list")
    if not isinstance(path, Path):
        raise TypeError("path must be a Path object")
    return path.suffix in extensions
