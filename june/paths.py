import os
from pathlib import Path
from sys import argv

directory = Path(
    os.path.abspath(__file__)
).parent


def path_for_flag(flag):
    try:
        path = argv[argv.index(f"--{flag}") + 1]
    except (IndexError, ValueError):
        path = str(directory.parent / flag)

    return Path(path)


data_path = path_for_flag("data")
configs_path = path_for_flag("configs")
