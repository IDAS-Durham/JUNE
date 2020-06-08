from glob import glob
from os import remove

import pytest


@pytest.fixture(
    autouse=True,
    scope="session"
)
def remove_log_files():
    yield
    for file in glob("*.log*"):
        remove(file)
