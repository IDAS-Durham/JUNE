from covid.infection import infection as infect
from covid.infection import symptons as sym
from covid.infection import transmission as trans

from covid import World
from covid.time import Timer 

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


@pytest.fixture(name="symptoms", scope="session")
def create_symptoms():
    return sym.SymptomsGaussian(health_index=None, mean_time=1.0, sigma_time=3.0)

@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(proabability=0.3)
