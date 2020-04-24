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
    with open("config_ne.yaml", "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    timer = Timer(config['time'])
    return timer 

if __name__ == '__main__':

    create_timer()
