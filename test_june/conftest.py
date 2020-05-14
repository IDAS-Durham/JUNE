import os
from glob import glob
from os import remove
from pathlib import Path

import pytest

directory = Path(
    os.path.abspath(__file__)
).parent


@pytest.fixture(
    autouse=True,
    scope="session"
)
def remove_log_files():
    yield
    for file in glob("*.log*"):
        remove(file)
