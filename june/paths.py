import os
from pathlib import Path
from sys import argv

directory = Path(
    os.path.abspath(__file__)
).parent


def path_for_flag(flag: str) -> Path:
    """
    Get a path input using a flag when the program is run.

    If no such argument is given default to the directory above
    the june with the name of the flag appended.

    e.g. --data indicates where the data folder is and defaults
    to june/../data

    Parameters
    ----------
    flag
        A string such as "data" which corresponds to the flag --data

    Returns
    -------
    A path
    """
    try:
        path = argv[argv.index(f"--{flag}") + 1]
    except (IndexError, ValueError):
        path = str(directory.parent / flag)

    return Path(path)


data_path = path_for_flag("data")
configs_path = path_for_flag("configs")
