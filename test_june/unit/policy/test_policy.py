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
from june.policy import Policy, PermanentPolicy, CloseSchools, CloseCompanies, Quarantine, Shielding, Policies, SocialDistancing
from june.simulator import Simulator


path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionTrajectoriesXNExp.yaml"
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
    worker.area = super_area
    household.add(worker, subgroup_type=household.SubgroupType.adults)
    worker.sector = "Q"
    company.add(worker)

    pupil = Person.from_attributes(age=6)
    pupil.area = super_area
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
    person.health_information.time_of_symptoms_onset = 5.3


class TestPolicy:
    def test__is_active(self):
        policy = Policy(start_time=datetime(2020, 5, 6), end_time=datetime(2020, 6, 6))
        assert policy.is_active(datetime(2020, 6, 6))
        assert not policy.is_active(datetime(2020, 6, 7))


class TestDefaultPolicy:
    def test__default_policy_adults(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        permanent_policy = PermanentPolicy()
        policies = Policies([permanent_policy])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
        date = datetime(2019, 2, 1)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        assert policies.must_stay_at_home(worker, date, None)
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
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
        sim.move_people_to_active_subgroups(
            ["hospital", "primary_activity", "residence"],
        )
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "hospitalised")
        sim.update_health_status(0.0, 0.0)
        sim.move_people_to_active_subgroups(
            ["hospital", "primary_activity", "residence"],
        )
        assert worker in worker.hospital.people
        assert pupil in pupil.primary_activity.people
        worker.health_information = None
        sim.clear_world()

    def test__default_policy_kids(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        permanent_policy = PermanentPolicy()
        policies = Policies([permanent_policy])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
        date = datetime(2019, 2, 1)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(pupil, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        assert policies.must_stay_at_home(pupil, date, None)
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
        assert worker in worker.residence.people
        assert pupil in pupil.residence.people
        pupil.health_information = None
        sim.clear_world()


class TestClosure:
    def test__close_schools(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        school_closure = CloseSchools(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 10, 1),
            years_to_close=[6],
        )
        policies = Policies([school_closure])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.apply_activity_ban(pupil, time_during_policy, activities) == ['residence']
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert pupil in pupil.residence.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.apply_activity_ban(pupil, time_after_policy, activities) == ['primary_activity', 'residence']
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        company_closure = CloseCompanies(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 10, 1),
            sectors_to_close = ['Q']
        )
        policies = Policies([company_closure])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.apply_activity_ban(worker, time_during_policy, activities) == ['residence']
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.apply_activity_ban(worker, time_after_policy, activities) == ['primary_activity', 'residence']
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_other_sector(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        company_closure = CloseCompanies(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 10, 1),
            sectors_to_close = ['R']
        )
        policies = Policies([company_closure])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.apply_activity_ban(worker, time_during_policy, activities) == ['primary_activity', 'residence']
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.primary_activity.people
        sim.clear_world()

class TestShielding:
    def test__old_people_shield(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        shielding = Shielding(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 10, 1),
            min_age=30)
        policies = Policies([shielding])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.must_stay_at_home(worker, time_during_policy, activities)
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()


class TestQuarantine:
    def test__symptomatic_stays_for_one_week(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        quarantine = Quarantine(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 30),
            n_days=7,
            n_days_household=14
        )
        policies = Policies([quarantine])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        assert policies.must_stay_at_home(worker, time_during_policy, 6.)
        sim.move_people_to_active_subgroups(activities, time_during_policy, 6.)
        assert worker in worker.residence.people
        worker.health_information = None
        sim.clear_world()


    def test__housemates_stay_for_two_weeks(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        quarantine = Quarantine(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 30),
            n_days=7,
            n_days_household=14
        )
        policies = Policies([quarantine])
        sim = Simulator.from_file(
            world, interaction, selector, policies, config_filename=test_config
        )
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        # before symptoms onset
        assert not policies.must_stay_at_home(pupil, time_during_policy, 4.)
        # after symptoms onset
        assert policies.must_stay_at_home(pupil, time_during_policy, 8.)
        sim.move_people_to_active_subgroups(activities, time_during_policy, 8.)
        assert pupil in pupil.residence.people
        # more thatn two weeks after symptoms onset
        assert not policies.must_stay_at_home(pupil, time_during_policy, 25.)
        worker.health_information = None
        sim.clear_world()

def test__social_distancing(super_area, selector, interaction):
    pupil, worker, world = make_dummy_world(super_area)
    start_date = datetime(2020, 3, 10)
    end_date = datetime(2020, 3, 12)
    social_distance = SocialDistancing(
        start_time=start_date, end_time=end_date
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
