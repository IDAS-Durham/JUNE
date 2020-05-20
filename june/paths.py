import logging
import os
from pathlib import Path
from sys import argv

logger = logging.getLogger(
    __name__
)

project_directory = Path(
    os.path.abspath(__file__)
).parent.parent

working_directory = Path(
    os.getcwd()
)


def find_default(name: str) -> Path:
    """


    Parameters
    ----------
    name

    Returns
    -------

    """
    cwd_default = working_directory / name
    if os.path.exists(
            cwd_default
    ):
        return cwd_default
    return project_directory / name


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
        path = Path(argv[argv.index(flag) + 1])
    except (IndexError, ValueError):
        path = find_default(name)
        logger.warning(
            f"No {flag} argument given - defaulting to:\n{path}"
        )

    if not path.exists():
        raise FileNotFoundError(
            f"No such folder {path}"
        )

    return path


data_path = path_for_name("data")
configs_path = path_for_name("configs")
