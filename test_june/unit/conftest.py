<<<<<<< HEAD:test_covid/unit/conftest.py
from covid.infection import infection as infect
from covid.infection import symptoms as sym
from covid.infection import transmission as trans
import covid.interaction as inter
from covid.simulator import Simulator
=======
from june.infection import infection as infect
from june.infection import symptoms as sym
from june.infection import transmission as trans
>>>>>>> master:test_june/unit/conftest.py

from june import world
from june.time import Timer 

import os
from pathlib import Path

import pytest
import yaml

<<<<<<< HEAD:test_covid/unit/conftest.py
from covid.groups.people.health_index import HealthIndex
from covid import World
from covid.time import Timer
=======
from june import World
from june.time import Timer
>>>>>>> master:test_june/unit/conftest.py

test_directory = Path(__file__).parent.parent


@pytest.fixture(name="config")
def read_config():
    return world.read_config(test_directory / "config_ne.yaml")

@pytest.fixture(name="world_ne", scope="session")
def create_world_northeast():
    return World(test_directory / "config_ne.yaml")

@pytest.fixture(name="world_box", scope="session")
def create_box_world():
    return World(box_mode=True, box_n_people=100)

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
    reference_health_index = HealthIndex().get_index_for_age(40)
    return sym.SymptomsConstant(health_index=reference_health_index) 

@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(probability=0.3)

@pytest.fixture(name="infection", scope="session")
def create_infection(transmission, symptoms):
    return infect.Infection(transmission, symptoms)

@pytest.fixture(name="interaction", scope="session")
def create_interaction():
    return inter.DefaultInteraction()

@pytest.fixture(name="simulator", scope="session")
def create_simulator(world_ne, interaction, infection):
    return Simulator.from_file(world_ne, interaction, infection)

@pytest.fixture(name="simulator_box", scope="session")
def create_simulator_box(world_box, interaction, infection):
    config_file = Path(__file__).parent.parent.parent / "configs/config_boxmode_example.yaml"
    return Simulator.from_file(world_box, interaction, infection, config_filename=config_file)
