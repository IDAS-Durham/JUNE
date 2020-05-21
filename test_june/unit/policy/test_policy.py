import pytest
import random
from pathlib import Path

from june.geography import Geography
from june.demography import Demography
from june.world import World
from june.interaction import DefaultInteraction
from june.infection import InfectionSelector, Infection
from june.infection import Symptom_Tags, SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.simulator import Simulator


path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
)
test_config = Path(__file__).parent.parent.parent / "test_simulator.yaml"


@pytest.fixture(name="world", scope="module")
def create_world():
    geography = Geography.from_file({"msoa": ["E00088544", "E02002560", "E02002559"]})
    geography.hospitals = Hospitals.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.care_homes = CareHomes.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    demography = Demography.for_geography(geography)
    world = World(geography, demography, include_households=True, include_commute=True)


@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file(constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7


@pytest.fixture(name="interaction", scope="module")
def create_interaction(selector):
    interaction = DefaultInteraction.from_file()
    interaction.selector = selector


def test__social_distancing(world, selector, interaction):

    start_date = 3
    end_date = 6
    social_distance = Policy(
        policy="social_distance", start_date=start_date, end_date=end_date
    )
    policies = Policies([social_distance])

    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )
    initial_betas = sim.interaction.betas.copy()
    for day in sim.timer:
        if day > sim.timer.total_days:
            break
        if day > start_date and day < end_date:
            for group in sim.interaction.betas.keys():
                assert sim.interaction.betas[group] == initial_betas[group] / 2
        else:
            assert sim.interaction.betas == initial_betas


def test__close_schools_years(world, selector, interaction):
    start_date = 3
    end_date = 6
    social_distance = Policy(
        policy="close_schools", start_date=start_date, end_date=end_date, years = [5,6,7],
    )
    policies = Policies([social_distance])

    school_kids = []
    for school in world.schools.members:
        school_kids += school.people

    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )

    for day in sim.timer:
        if day > sim.timer.total_days:
            break
        if day > start_date and day < end_date:
            assert 
        else:
            assert sim.interaction.betas == initial_betas




def test__close_schools_sectors(world, selector, interaction):
    pass
