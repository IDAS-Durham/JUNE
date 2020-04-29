from covid.infection import infection as infect
from covid.infection import symptons as sym
from covid.infection import transmission as trans

from covid import World
from covid.time import Timer 
import os
import pytest
import yaml

@pytest.fixture(name="world_ne", scope="session")
def create_world_northeast():
    world = World("config_ne.yaml")
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
    return sym.SymptomsConstant(health_index=None, recovery_rate=0.3)

@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(start_time=0.0, proabability=0.3)