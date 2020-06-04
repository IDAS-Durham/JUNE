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
                if group != 'household':
                    assert sim.interaction.betas[group] == initial_betas[group] / 2
                else:
                    assert sim.interaction.betas[group] == initial_betas[group]
        else:
            assert sim.interaction.betas == initial_betas


def test__close_schools_years(world, selector, interaction):
    start_date = 3
    end_date = 6
    school_closure = Policy(
        policy="close_schools", start_date=start_date, end_date=end_date, years = [5,6,7],
    )
    policies = Policies([school_closure])

    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )

    activities = ['primary_activity']
    for day in sim.timer:
        sim.move_people_to_active_subgroups(activities)
        if day > sim.timer.total_days:
            break
        for school in world.schools.members:
            school_age_range = np.arange(school.age_min, school.age_max+1)
            school_years = dict(zip(school_age_range, np.arange(1,len(school.subgroups)+1)))
            for year in years:
                year_subgroup_idx = school.get(year, None)
                if year_subgroup_idx is not None:
                    if day > start_date and day < end_date:
                        assert len(school.subgroup[year_subgroup_idx].people == 0)

        sim.clear_world()



def test__close_sectors(world, selector, interaction):
    #TODO: test that if sector is closed, person does not commute
    start_date = 3
    end_date = 6
    sector_closure = Policy(
        policy="close_companies", start_date=start_date, end_date=end_date, sectors = ['A', 'B'],
    )
    policies = Policies([sector_closure])

    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )

    activities = ['primary_activity']
    for day in sim.timer:
        sim.move_people_to_active_subgroups(activities)
        if day > sim.timer.total_days:
            break
        for company in world.companies.members:
            if company.sector == sector:
                if day > start_date and day < end_date:
                    assert len(company.people == 0)

        sim.clear_world()

def test__close_pubs(world, selector, interaction):
    start_date = 3
    end_date = 6
    sector_closure = Policy(
        policy="close", groups='pubs', start_date=start_date, end_date=end_date,
    )
    policies = Policies([sector_closure])

    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )

    activities = ['leisure']
    for day in sim.timer:
        sim.move_people_to_active_subgroups(activities)
        if day > sim.timer.total_days:
            break
        for pub in world.pubs.members:
            if day > start_date and day < end_date:
                assert len(pub.people == 0)

        sim.clear_world()
