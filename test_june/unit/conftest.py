from june.infection import infection as infect
from june.infection import symptoms as sym
from june.infection import transmission as trans
import june.interaction as inter
from june.infection.health_index import HealthIndexGenerator
from june.simulator import Simulator
from june import world
from june.time import Timer 

import os
from pathlib import Path

import pytest
import yaml

test_directory = Path(__file__).parent.parent


@pytest.fixture(name="config")
def read_config():
    return world.read_config(test_directory / "config_ne.yaml")

@pytest.fixture(name="world_ne", scope="session")
def create_world_northeast():
    return world.World(test_directory / "config_ne.yaml")

@pytest.fixture(name="world_box", scope="session")
def create_box_world():
    return world.World(box_mode=True, box_n_people=100)

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
        return sym.SymptomsGaussian(mean_time=1.0, sigma_time=3.0)


@pytest.fixture(name="symptoms_constant", scope="session")
def create_symptoms_constant():
    return sym.SymptomsConstant()

@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(probability=0.3)

@pytest.fixture(name="infection", scope="session")
def create_infection(transmission, symptoms):
    return infect.Infection(transmission, symptoms)

@pytest.fixture(name="infection_constant", scope="session")
def create_infection_constant(transmission, symptoms_constant):
    return infect.Infection(transmission, symptoms_constant)


@pytest.fixture(name="interaction", scope="session")
def create_interaction():
    return inter.DefaultInteraction.from_file()

@pytest.fixture(name="simulator", scope="session")
def create_simulator(world_ne, interaction, infection_constant):
    return Simulator.from_file(world_ne, interaction, infection_constant,
            config_filename = test_directory / "config_ne.yaml")

@pytest.fixture(name="simulator_box", scope="session")
def create_simulator_box(world_box, interaction, infection):
    config_file = Path(__file__).parent.parent.parent / "configs/config_boxmode_example.yaml"
    return Simulator.from_file(world_box, interaction, infection, config_filename=config_file)
