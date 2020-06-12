import pytest
import random
from pathlib import Path
from june import paths
from datetime import datetime
import copy

from june.demography.geography import Geography
from june.demography import Person 
from june.world import World
from june.interaction import ContactAveraging
from june.infection import Infection
from june.infection.infection import InfectionSelector
from june.groups import Hospital, School, Company, Household
from june.groups import Hospitals, Schools, Companies, Households
from june.groups.leisure import Cinemas, Pubs, Groceries
from june.policy import Policy, Policies
from june.simulator import Simulator


path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
)
test_config = paths.configs_path / "tests/test_simulator.yaml"


@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file(constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector

@pytest.fixture(name="interaction", scope="module")
def create_interaction(selector):
    interaction = ContactAveraging.from_file(selector=selector)
    return interaction

@pytest.fixture(name="super_area", scope="module")
def create_geography():
    g = Geography.from_file(filter_key={"super_area" : ["E02002559"]})
    return g.super_areas.members[0]

@pytest.fixture(name='company', scope='module')
def make_company(super_area):
    return Company(
            super_area = super_area,
            n_workers_max=100,
            sector='Q'
            )

@pytest.fixture(name='school', scope='module')
def make_school(super_area):
    return School(
            coordinates=super_area.coordinates,
            n_pupils_max=100,
            age_min=4,
            age_max=10,
            sector='primary'
            )

@pytest.fixture(name='household', scope='module')
def make_household():
    return Household()

@pytest.fixture(name='hospital', scope='module')
def make_hospital(super_area):
    return Hospital(n_beds=40, n_icu_beds=5, super_area = super_area.name, coordinates=super_area.coordinates)

def make_worker(company, household):
    worker = Person.from_attributes(age=40)
    household.add(worker, subgroup_type=household.SubgroupType.adults)
    worker.sector = 'Q'
    company.add(worker)
    return worker

def make_pupil(school, household):
    pupil = Person.from_attributes(age=6)
    household.add(pupil, subgroup_type=household.SubgroupType.kids)
    school.add(pupil)
    return pupil 


def make_dummy_world(school, company, hospital, household):
    world = World()
    world.schools = Schools([school])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household])
    return world

def infect_person(person, selector, symptom_tag='influenza'):
    sim.selector.infect_person_at_time(person, 0.0)
    person.health_information.infection.symptoms.tag = getattr(SymptomTag,symptom_tag)
    sim.update_health_status(0.0, 0.0)


class TestDefaultPolicy():
    def test__default_policy_adults(self, school, company, hospital, household, selector, interaction):
        # Adult ill stays at home
        pupil = make_pupil(school, household)
        worker = make_worker(company, household)
        world = make_dummy_world(school, company, hospital, household)
        default_policy = Policy()
        policies = Policies([default_policy])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(['primary_activity', 'residence'])
        assert worker in  worker.primary_activity.people
        assert pupil in  pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, 'influenza')
        assert policies.must_stay_at_home(worker, None, None)
        # Adult ill  in hospital goes to hospital

'''
def test__default_policy_kids(world, selector, interaction):
    default_policy = Policy()
    # kid ill stays at home
    # kid ill drags parent
    # kid goes to hospital if needs to
    policies = Policies([default_policy])
    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )
    for time in sim.timer():
        if time > sim.timer.final_date:
            break


        

def test__kid_at_home_is_supervised(world, selector, interaction, health_index):

    kids_at_school = []
    for person in sim.world.people.members:
        if person.primary_activity is not None and person.age < sim.min_age_home_alone:
            kids_at_school.append(person)

    for kid in kids_at_school:
        sim.selector.infect_person_at_time(kid, 0.0)
        kid.health_information.infection.symptoms.tag = SymptomTag.influenza
        assert kid.health_information.must_stay_at_home

    sim.move_people_to_active_subgroups(["primary_activity", "residence"])

    for kid in kids_at_school:
        assert kid in kid.residence.people
        guardians_at_home = [
            person for person in kid.residence.group.people if person.age >= 18
        ]
        assert len(guardians_at_home) != 0

    sim.clear_world()


 

def test__social_distancing(world, selector, interaction):

    start_date = datetime(2020, 3, 10)
    end_date = datetime(2020, 3, 12)
    social_distance = Policy(
        policy="social_distance", start_time=start_date, end_time=end_date
    )
    policies = Policies([social_distance])

    sim = Simulator.from_file(
        world, interaction, selector, policies, config_filename=test_config
    )
    initial_betas = copy.deepcopy(sim.interaction.beta)
    for time in sim.timer:
        if time > sim.timer.final_date:
            break
        if sim.timer.date > start_date and sim.timer.date < sim.timer.date:
            for group in sim.interaction.betas:
                if group != 'household':
                    assert sim.interaction.beta[group] == initial_betas[group] * 0.5
                else:
                    assert sim.interaction.beta[group] == initial_betas[group]
        else:
            assert sim.interaction.beta == initial_betas
'''

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
