import os
from pathlib import Path
from sys import argv

directory = Path(
    os.path.abspath(__file__)
).parent

try:
    data_path = argv[argv.index("--data") + 1]
except (IndexError, ValueError):
    data_path = str(directory.parent / "data")

data_path = Path(data_path)
