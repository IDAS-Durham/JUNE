import os
from pathlib import Path

import pytest
import yaml

from covid import World
from covid.time import Timer

test_directory = Path(__file__).parent.parent


@pytest.fixture(name="world_ne", scope="session")
def create_world_northeast():
    world = World(test_directory / "config_ne.yaml")
    return world


@pytest.fixture(name="test_timer", scope="session")
def create_timer():
    config_dir = os.path.join(
        os.path.dirname(
            os.path.realpath(__file__)
        ),
    )
    with open("config_ne.yaml") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    return Timer(config['time'])
