from june.infection import Infection
from june.infection import symptoms as sym
from june.infection import transmission as trans
import june.interaction as inter
from june.infection.health_index import HealthIndexGenerator
from june.simulator import Simulator
from june.demography.geography import Geography
from june.demography import Demography
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries
from june import World

import os
from pathlib import Path

import pytest
import yaml

test_directory = Path(__file__).parent.parent

def pytest_addoption(parser):
    parser.addoption("--data", action="store", default=os.path.join(Path(os.getcwd()).parent, "data"))
    parser.addoption("--configs", action="store", default=os.path.join(Path(os.getcwd()).parent, "configs"))

@ pytest.fixture()
def data(pytestconfig):
    return pytestconfig.getoption("data")

@pytest.fixture()
def configs(pytestconfig):
    return pytestconfig.getoption("configs")

@pytest.fixture(name="symptoms", scope="session")
def create_symptoms():
    return sym.SymptomsGaussian(health_index=None, mean_time=1.0, sigma_time=3.0)


@pytest.fixture(name="symptoms_constant", scope="session")
def create_symptoms_constant():
    return sym.SymptomsConstant()

@pytest.fixture(name="symptoms_healthy", scope="session")
def create_symptoms_healthy():
    return sym.SymptomsHealthy()



@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(probability=0.3)


@pytest.fixture(name="infection", scope="session")
def create_infection(transmission, symptoms):
    return Infection(transmission, symptoms)


@pytest.fixture(name="infection_constant", scope="session")
def create_infection_constant(transmission, symptoms_constant):
    return Infection(transmission, symptoms_constant)

@pytest.fixture(name="infection_healthy", scope="session")
def create_infection_healthy(transmission, symptoms_healthy):
    return infect.Infection(transmission, symptoms_healthy)

@pytest.fixture(name="interaction", scope="session")
def create_interaction():
    return inter.DefaultInteraction.from_file()

@pytest.fixture(name="geography", scope="session")
def make_geography():
    geography = Geography.from_file(
        {"msoa": ["E02002512", "E02001697"]}
    )
    return geography


@pytest.fixture(name="world", scope="session")
def create_world(geography):
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.companies = Companies.for_geography(geography)
    world = World(geography, demography, include_households=True)
    return world

@pytest.fixture(name="simulator", scope="session")
def create_simulator(world, interaction, infection_constant):
    return Simulator.from_file(world, interaction, infection_constant)

@pytest.fixture(name="world_box", scope="session")
def create_box_world():
    geography = Geography.from_file(
        {"msoa": ["E02001697"]}
    )
    return World.from_geography(geography, box_mode=True)

@pytest.fixture(name="simulator_box", scope="session")
def create_simulator_box(request, world_box, interaction, infection_healthy):
    path_to_config = request.config.getoption("configs")
    config_file = (
        os.path.join(path_to_config, "config_boxmode_example.yaml"
    ))
    return Simulator.from_file(
        world_box, interaction, infection_healthy, config_filename=config_file
    )
