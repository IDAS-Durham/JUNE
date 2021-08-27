import logging
import os
import subprocess
from pathlib import Path
from sys import argv

logger = logging.getLogger(__name__)

project_directory = Path(os.path.abspath(__file__)).parent

working_directory = Path(os.getcwd())

working_directory_parent = working_directory.parent


def find_default(name: str, look_in_package=True) -> Path:
    """
    Get a default path when no command line argument is passed.

    - First attempt to find the folder in the current working directory.
    - If it is not found there then try the directory in which June lives.
    - Finally, try the directory above the current working directory. This
    is for the build pipeline.

    This means that tests will find the configuration regardless of whether
    they are run together or individually.

    Parameters
    ----------
    name
        The name of some folder

    Returns
    -------
    The full path to that directory
    """
    directories_to_look = [working_directory, working_directory_parent]
    if look_in_package:
        directories_to_look.append(project_directory)
        directories_to_look.append(project_directory.parent)
    for directory in directories_to_look:
        path = directory / name
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Could not find a default path for {name}")


def path_for_name(name: str, look_in_package=True) -> Path:
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
        if not path.exists():
            raise FileNotFoundError(f"No such folder {path}")
    except (IndexError, ValueError):
        path = find_default(name, look_in_package=look_in_package)
        logger.warning(f"No {flag} argument given - defaulting to:\n{path}")

    return path


try:
    data_path = path_for_name("data", look_in_package=True)
except FileNotFoundError:
    answer = input(
        "I couldn't find any data folder, do you want me to download it for you? (y/N) "
    )
    if answer == "y":
        script_path = Path(__file__).parent.parent / "scripts" / "get_june_data.sh"
        with open(script_path, 'rb') as file:
            script = file.read()
        rc = subprocess.call(script, shell=True)
    data_path = path_for_name("data", look_in_package=True)

configs_path = path_for_name("configs")
