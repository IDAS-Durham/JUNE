import pytest
import random
from pathlib import Path
from june import paths
from datetime import datetime
import copy

from june.demography.geography import Geography
from june.demography import Person, Population
from june.world import World
from june.interaction import ContactAveraging
from june.infection import Infection
from june.infection import SymptomTag
from june.infection.infection import InfectionSelector
from june.groups import Hospital, School, Company, Household
from june.groups import Hospitals, Schools, Companies, Households
from june.groups.leisure import Cinemas, Pubs, Groceries
from june.policy import PermanentPolicy, CloseSchools, CloseCompanies, Policies
from june.simulator import Simulator


path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
)
test_config = paths.configs_path / "tests/test_simulator_simple.yaml"


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
    g = Geography.from_file(filter_key={"super_area": ["E02002559"]})
    return g.super_areas.members[0]

def make_dummy_world(super_area):
    company = Company(super_area=super_area, n_workers_max=100, sector="Q")
    school = School(
        coordinates=super_area.coordinates,
        n_pupils_max=100,
        age_min=4,
        age_max=10,
        sector="primary",
    )
    household = Household()
    hospital = Hospital(
        n_beds=40,
        n_icu_beds=5,
        super_area=super_area.name,
        coordinates=super_area.coordinates,
    )
    worker = Person.from_attributes(age=40)
    worker.area=super_area
    household.add(worker, subgroup_type=household.SubgroupType.adults)
    worker.sector = "Q"
    company.add(worker)

    pupil = Person.from_attributes(age=6)
    pupil.area=super_area
    household.add(pupil, subgroup_type=household.SubgroupType.kids)
    school.add(pupil)

    world = World()
    world.schools = Schools([school])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household])
    world.companies = Companies([company])
    world.people = Population([worker, pupil])
    return pupil, worker, world


def infect_person(person, selector, symptom_tag="influenza"):
    selector.infect_person_at_time(person, 0.0)
    person.health_information.infection.symptoms.tag = getattr(SymptomTag, symptom_tag)

class TestPolicy:
    def test__always_active():
        permanent_policy = PermanentPolicy()
        assert permanent_policy.is_active(datetime(2500,1,1))

    def test__is_active():
        policy = Policy(start_time=datetime(2020,5,6), end_time=datetime(2020, 6,6))
        assert policy.is_active(datetime(2020,6,6))
        assert not policy.is_active(datetime(2020,6,7))

class TestDefaultPolicy:
    def test__default_policy_adults(
        self, super_area, selector, interaction
    ):
        pupil, worker, world = make_dummy_world(super_area)
        permanent_policy = PermanentPolicy()
        policies = Policies([permanent_policy])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(["primary_activity", "residence"])
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        assert policies.must_stay_at_home(worker, None, None)
        sim.move_people_to_active_subgroups(["primary_activity", "residence"])
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        worker.health_information = None
        sim.clear_world()

    def test__default_policy_adults_still_go_to_hospital(
        self, super_area, selector, interaction
    ):
        pupil, worker, world = make_dummy_world(super_area)
        permanent_policy = PermanentPolicy()
        policies = Policies([permanent_policy])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(["hospital", "primary_activity", "residence"])
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "hospitalised")
        sim.update_health_status(0.0, 0.0)
        sim.move_people_to_active_subgroups(["hospital", "primary_activity", "residence"])
        assert worker in worker.hospital.people
        assert pupil in pupil.primary_activity.people
        worker.health_information = None
        sim.clear_world()
 
    def test__default_policy_kids(
        self, super_area, selector, interaction
    ):
        pupil, worker, world = make_dummy_world(super_area)
        permanent_policy = PermanentPolicy()
        policies = Policies([permanent_policy])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(["primary_activity", "residence"])
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(pupil, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        assert policies.must_stay_at_home(pupil, None, None)
        sim.move_people_to_active_subgroups(["primary_activity", "residence"])
        assert worker in worker.residence.people
        assert pupil in pupil.residence.people
        pupil.health_information = None
        sim.clear_world()
 

class TestClosure:
    def test__close_schools(
        self, super_area, selector, interaction
    ):
        pupil, worker, world = make_dummy_world(super_area)
        school_closure = CloseSchools(datetime(2020,1,1), datetime(2030,1,1),
                years_to_close=[6])
        policies = Policies([school_closure])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        assert policies.must_stay_at_home(pupil, None, None)
        sim.move_people_to_active_subgroups(["primary_activity", "residence"])
        assert worker in worker.residence.people
        assert pupil in pupil.residence.people
        sim.clear_world()





"""
def test__default_policy_kids(world, selector, interaction):
    permanent_policy = Policy()
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
                if group != "household":
                    assert sim.interaction.beta[group] == initial_betas[group] * 0.5
                else:
                    assert sim.interaction.beta[group] == initial_betas[group]
        else:
            assert sim.interaction.beta == initial_betas
"""

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
