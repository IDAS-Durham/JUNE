import copy
from datetime import datetime
from pathlib import Path

import pytest

from june import paths
from june.demography.geography import Geography
from june.demography import Demography
from june.world import World, generate_world_from_geography
from june.interaction import ContactAveraging
from june.infection import Infection
from june.infection.transmission import TransmissionConstant
from june.infection.infection import InfectionSelector
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    CareHomes,
    Cemeteries,
    Universities,
)
from june.groups.leisure import leisure, Cinemas, Pubs, Groceries
from june.interaction import ContactAveraging
from june.policy import Policy, Policies
from june.seed import Seed
from june.simulator import Simulator
from june.world import generate_world_from_geography

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
)
test_config = paths.configs_path / "tests/test_simulator.yaml"


@pytest.fixture(name="world", scope="module")
def create_world():
    geography = Geography.from_file(
        {"super_area": ["E02003282", "E02002560", "E02002559"]}
    )
    geography.hospitals = Hospitals.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.care_homes = CareHomes.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.universities = Universities.for_super_areas(geography.super_areas)
    world = generate_world_from_geography(
        geography, include_households=True, include_commute=True
    )
    world.cinemas = Cinemas.for_geography(geography)
    world.pubs = Pubs.for_geography(geography)
    world.groceries = Groceries.for_super_areas(
        world.super_areas, venues_per_capita=1 / 500
    )
    world.cemeteries = Cemeteries()
    return world


@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file(config_filename=constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.fixture(name="interaction", scope="module")
def create_interaction(selector):
    interaction = ContactAveraging.from_file(selector=selector)
    # interaction.selector = selector
    return interaction


def test__social_distancing(world, selector, interaction):
    start_date = datetime(2020, 3, 10)
    end_date = datetime(2020, 3, 12)
    social_distance = Policy(
        policy="social_distance", start_time=start_date, end_time=end_date
    )
    policies = Policies.from_file([social_distance])
    interaction = ContactAveraging.from_file(selector=selector)

    seed = Seed(world.super_areas, selector,)
    n_cases = 10
    seed.unleash_virus(n_cases)  # play around with the initial number of cases
    leisure_instance = leisure.generate_leisure_for_config(
        world=world, config_filename=test_config
    )

    simulator = Simulator.from_file(
        world,
        interaction,
        selector,
        policies,
        config_filename=test_config,
        leisure=leisure_instance,
    )
    simulator.timer.reset()
    initial_betas = copy.deepcopy(simulator.interaction.beta)

    simulator.clear_world()
    for time in simulator.timer:
        if time > simulator.timer.final_date:
            break
        if simulator.seed:
            if (time >= simulator.seed.min_date) and (time <= simulator.seed.max_date):
                simulator.seed.unleash_virus_per_region(time)
        simulator.do_timestep()
        if simulator.timer.date >= start_date and simulator.timer.date < end_date:
            for group in simulator.interaction.beta:
                print(group)
                if group != "household":
                    assert (
                        simulator.interaction.beta[group] == initial_betas[group] * 0.5
                    )
                else:
                    assert simulator.interaction.beta[group] == initial_betas[group]
        else:
            assert simulator.interaction.beta == initial_betas


# def test__close_schools_years(world, selector, interaction):
#     start_date = 3
#     end_date = 6
#     school_closure = Policy(
#         policy="close_schools", start_date=start_date, end_date=end_date, years = [5,6,7],
#     )
#     policies = Policies([school_closure])

#     sim = Simulator.from_file(
#         world, interaction, selector, policies, config_filename=test_config
#     )

#     activities = ['primary_activity']
#     for day in sim.timer:
#         sim.move_people_to_active_subgroups(activities)
#         if day > sim.timer.total_days:
#             break
#         for school in world.schools.members:
#             school_age_range = np.arange(school.age_min, school.age_max+1)
#             school_years = dict(zip(school_age_range, np.arange(1,len(school.subgroups)+1)))
#             for year in years:
#                 year_subgroup_idx = school.get(year, None)
#                 if year_subgroup_idx is not None:
#                     if day > start_date and day < end_date:
#                         assert len(school.subgroup[year_subgroup_idx].people == 0)

#         sim.clear_world()


# def test__close_sectors(world, selector, interaction):
#     #TODO: test that if sector is closed, person does not commute
#     start_date = 3
#     end_date = 6
#     sector_closure = Policy(
#         policy="close_companies", start_date=start_date, end_date=end_date, sectors = ['A', 'B'],
#     )
#     policies = Policies([sector_closure])

#     sim = Simulator.from_file(
#         world, interaction, selector, policies, config_filename=test_config
#     )

#     activities = ['primary_activity']
#     for day in sim.timer:
#         sim.move_people_to_active_subgroups(activities)
#         if day > sim.timer.total_days:
#             break
#         for company in world.companies.members:
#             if company.sector == sector:
#                 if day > start_date and day < end_date:
#                     assert len(company.people == 0)

#         sim.clear_world()

# def test__close_pubs(world, selector, interaction):
#     start_date = 3
#     end_date = 6
#     sector_closure = Policy(
#         policy="close", groups='pubs', start_date=start_date, end_date=end_date,
#     )
#     policies = Policies([sector_closure])

#     sim = Simulator.from_file(
#         world, interaction, selector, policies, config_filename=test_config
#     )

#     activities = ['leisure']
#     for day in sim.timer:
#         sim.move_people_to_active_subgroups(activities)
#         if day > sim.timer.total_days:
#             break
#         for pub in world.pubs.members:
#             if day > start_date and day < end_date:
#                 assert len(pub.people == 0)

#         sim.clear_world()
