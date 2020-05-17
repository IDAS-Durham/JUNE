from june.infection import infection as infect
from june.infection import symptoms as sym
from june.infection import symptoms_trajectory as strans
from june.infection import trajectory_maker as tmaker
from june.infection import transmission as trans
import june.interaction as inter
from june.infection.health_index import HealthIndexGenerator
from june.simulator import Simulator
from june import world
from june.time import Timer
from june.geography import Geography
from june.demography import Demography
from june.groups import Hospitals, Schools, Companies, CareHomes, Cemeteries
from june import World

import os
from pathlib import Path

import pytest
import yaml

test_directory = Path(__file__).parent.parent


@pytest.fixture(name="symptoms", scope="session")
def create_symptoms():
    return sym.SymptomsGaussian(health_index=[], mean_time=1.0, sigma_time=3.0)

@pytest.fixture(name="symptoms_constant", scope="session")
def create_symptoms_constant():
    reference_health_index = HealthIndexGenerator.from_file()(40, 'm')
    return sym.SymptomsConstant(health_index=reference_health_index)

@pytest.fixture(name="trajectories", scope="session")
def create_trajectories():
    return tmaker.TrajectoryMaker(None)

@pytest.fixture(name="symptoms_trajectories", scope="session")
def create_symptoms_trajectories(trajectories):
    return strans.SymptomsTrajectory(health_index=[0.1, 0.2, 0.3, 0.4, 0.5])

@pytest.fixture(name="transmission", scope="session")
def create_transmission():
    return trans.TransmissionConstant(probability=0.3)

@pytest.fixture(name="selector", scope="session")
def create_infection_selector():
    return infect.InfectionSelector(transmission_type="XNEXp")

@pytest.fixture(name="simpleselector", scope="session")
def create_infection_simpleselector():
    return infect.InfectionSelector(transmission_type="Constant",
                                    symptoms_type="Constant")

@pytest.fixture(name="infection", scope="session")
def create_infection(transmission, symptoms):
    return infect.Infection(transmission, symptoms)

@pytest.fixture(name="infection_constant", scope="session")
def create_infection_constant(transmission, symptoms_constant):
    return infect.Infection(transmission, symptoms_constant)

@pytest.fixture(name="interaction", scope="session")
def create_interaction():
    interaction          = inter.DefaultInteraction.from_file()
    interaction.selector = simpleselector
    return interaction

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
    geography.carehomes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.companies = Companies.for_geography(geography)
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
def create_simulator_box(world_box, interaction, infection):
    config_file = (
        Path(__file__).parent.parent.parent / "configs/config_boxmode_example.yaml"
    )
    return Simulator.from_file(
        world_box, interaction, infection, config_filename=config_file
    )
