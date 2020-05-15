import logging
import os
from pathlib import Path
from sys import argv

logger = logging.getLogger(
    __name__
)

directory = Path(
    # os.path.abspath(__file__)
    os.getcwd()
)  # .parent


def path_for_name(name: str) -> Path:
    """
    Get a path input using a flag when the program is run.

    If no such argument is given default to the directory above
    the june with the name of the flag appended.

    e.g. --data indicates where the data folder is and defaults
    to june/../data

    Parameters
    ----------
    name
        A string such as "data" which corresponds to the flag --data

    Returns
    -------
    A path
    """
    flag = f"--{name}"
    try:
        path = argv[argv.index(flag) + 1]
    except (IndexError, ValueError):
        path = str(directory.parent / name)
        logger.warning(
            f"No {flag} argument given - defaulting to:\n{path}"
        )

    return Path(path)


data_path = path_for_name("data")
configs_path = path_for_name("configs")
