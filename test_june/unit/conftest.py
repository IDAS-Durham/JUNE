# set seed
import random

import numba as nb
import numpy as np
import pytest

import june.infection.symptoms
import june.interaction as inter
from june import paths
from june.demography.geography import Geography
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries
from june.infection import Infection
from june.infection import InfectionSelector
from june.infection import infection as infect
from june.infection import trajectory_maker as tmaker
from june.infection import transmission as trans
from june.simulator import Simulator
from june.simulator_box import SimulatorBox
from june.world import generate_world_from_geography

constant_config = paths.configs_path / "defaults/infection/InfectionConstant.yaml"


@pytest.fixture(autouse=True)
def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit(cache=True)
    def set_seed_numba(seed):
        return np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return


@pytest.fixture()
def data(pytestconfig):
    return pytestconfig.getoption("data")


@pytest.fixture()
def configs(pytestconfig):
    return pytestconfig.getoption("configs")


@pytest.fixture(name="trajectories", scope="session")
def create_trajectories():
    return tmaker.TrajectoryMakers.from_file()


@pytest.fixture(name="symptoms", scope="session")
def create_symptoms(symptoms_trajectories):
    return symptoms_trajectories


@pytest.fixture(name="symptoms_trajectories", scope="session")
def create_symptoms_trajectories():
    return june.infection.symptoms.Symptoms(
        health_index=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    )


@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(probability=0.3)


@pytest.fixture(name="infection", scope="session")
def create_infection(transmission, symptoms):
    return Infection(transmission, symptoms)


@pytest.fixture(name="infection_constant", scope="session")
def create_infection_constant(transmission, symptoms_constant):
    return Infection(transmission, symptoms_constant)


@pytest.fixture(name="interaction", scope="session")
def create_interaction():
    interaction = inter.ContactAveraging.from_file()
    interaction.selector = infect.InfectionSelector.from_file(config_filename=constant_config)
    return interaction


@pytest.fixture(name="geography", scope="session")
def make_geography():
    geography = Geography.from_file(
        {"super_area": ["E02002512", "E02001697"]}
    )
    return geography


@pytest.fixture(name="world", scope="session")
def create_world(geography):
    geography.hospitals = Hospitals.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.companies = Companies.for_geography(geography)
    world = generate_world_from_geography(geography, include_households=True)
    return world


@pytest.fixture(name="simulator", scope="session")
def create_simulator(world, interaction, infection_constant):
    return Simulator.from_file(world, interaction, infection_constant)


@pytest.fixture(name="world_box", scope="session")
def create_box_world():
    geography = Geography.from_file(
        {"super_area": ["E02001697"]}
    )
    return generate_world_from_geography(geography, box_mode=True)


@pytest.fixture(name="simulator_box", scope="session")
def create_simulator_box(world_box, interaction):
    selector_file = paths.configs_path / "defaults/infection/InfectionConstant.yaml"
    config_file = paths.configs_path / "config_boxmode_example.yaml"
    selector = InfectionSelector.from_file(config_filename=selector_file)
    return SimulatorBox.from_file(
        world_box, interaction, selector, config_filename=config_file
    )


@pytest.fixture(name="world_visits", scope="session")
def make_super_areas():
    geo = Geography.from_file({"super_area": ["E02003353"]})
    geo.care_homes = CareHomes.for_geography(geo)
    world = generate_world_from_geography(geo, include_households=True)
    return world
