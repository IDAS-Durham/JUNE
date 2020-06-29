import copy
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from june import paths
from june.demography import Person, Population
from june.demography.geography import Geography
from june.groups import Hospital, School, Company, Household, University
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    CareHomes,
    Universities,
    Cemeteries,
)
from june.groups.leisure import leisure, Cinemas, Pubs, Cinema, Pub
from june.infection import SymptomTag
from june.infection.infection import InfectionSelector
from june.interaction import ContactAveraging
from june.policy import (
    Policy,
    PermanentPolicy,
    CloseSchools,
    CloseCompanies,
    CloseUniversities,
    Quarantine,
    Shielding,
    Policies,
    SocialDistancing,
    CloseLeisureVenue,
    ChangeLeisureProbability,
)
from june.simulator import Simulator
from june.world import World, generate_world_from_hdf5, generate_world_from_geography

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent
    / "configs/defaults/infection/InfectionTrajectoriesXNExp.yaml"
)
test_config = paths.configs_path / "tests/test_simulator_simple.yaml"


@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file(config_filename=constant_config)
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

@pytest.fixture(name="super_area_big", scope="module")
def create_big_geography():
    g = Geography.from_file(filter_key={"super_area": [
        "E02003282",
        "E02001720",
        "E00088544",
        "E02002560",
        "E02002559",
        "E02004314"]})
    return g


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
    world.universities = Universities([])
    world.companies = Companies([company])
    world.people = Population([worker, pupil])
    cinema = Cinema()
    cinema.coordinates = super_area.coordinates
    world.cinemas = Cinemas([cinema])
    pub = Pub()
    pub.coordinates = super_area.coordinates
    world.pubs = Pubs([pub])
    return pupil, worker, world

def make_dummy_world_with_university(super_area):
    university = University(coordinates=super_area.coordinates, n_students_max=100,)
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
    student = Person.from_attributes(age=21)
    student.area = super_area
    household.add(student, subgroup_type=household.SubgroupType.adults)
    university.add(student)

    pupil = Person.from_attributes(age=6)
    pupil.area = super_area
    household.add(pupil, subgroup_type=household.SubgroupType.kids)
    school.add(pupil)

    world = World()
    world.schools = Schools([school])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household])
    world.universities = Universities([university])
    world.companies = Companies([])
    world.people = Population([student, pupil])
    cinema = Cinema()
    cinema.coordinates = super_area.coordinates
    world.cinemas = Cinemas([cinema])
    pub = Pub()
    pub.coordinates = super_area.coordinates
    world.pubs = Pubs([pub])
    return pupil, student, world

def make_world(geography):
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.universities = Universities.for_super_areas(geography.super_areas)
    world = generate_world_from_geography(geography, include_households=False, include_commute=False)
    return world

def infect_person(person, selector, symptom_tag="influenza"):
    selector.infect_person_at_time(person, 0.0)
    person.health_information.infection.symptoms.tag = getattr(SymptomTag, symptom_tag)
    person.health_information.time_of_symptoms_onset = 5.3
    person.residence.group.quarantine_starting_date = 5.3


class TestPolicy:
    def test__is_active(self):
        policy = Policy(start_time="2020-5-6", end_time="2020-6-6")
        assert policy.is_active(datetime(2020, 6, 6))
        assert not policy.is_active(datetime(2020, 6, 7))

class TestLockdownStatus:
    def test__lockdown_status_random(self, super_area_big):
        world = make_world(super_area_big)

        found_worker = False
        found_child = False
        for person in world.areas[0].people:
            if person.age > 18:
                worker = person
                found_worker = True
            elif person.age < 18:
                child = person
                found_child = True
            if found_worker and found_child:
                break

        assert worker.lockdown_status is not None
        assert child.lockdown_status is None

    def test__lockdown_status_teacher(self, super_area_big):
        world = make_world(super_area_big)

        teacher = world.schools.members[0].teachers.people[0]
        assert teacher.lockdown_status == 'key_worker'

    def test__lockdown_status_medic(self, super_area_big):
        world = make_world(super_area_big)

        medic = world.hospitals.members[0].people[0]
        assert medic.lockdown_status == 'key_worker'

    def test__lockdown_status_care_home(self, super_area_big):
        world = make_world(super_area_big)

        care_home_worker = world.care_homes[0].people[0]
        assert care_home_worker.lockdown_status == 'key_worker'

class TestDefaultPolicy:
    def test__default_policy_adults(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        permanent_policy = PermanentPolicy()
        policies = Policies([permanent_policy])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        sim.clear_world()
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
        date = datetime(2019, 2, 1)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        assert policies.stay_home_collection(date=date)(worker, None)
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
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
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
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
        sim.clear_world()
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
        date = datetime(2019, 2, 1)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        infect_person(pupil, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        assert policies.stay_home_collection(date=date)(pupil, None)
        sim.move_people_to_active_subgroups(["primary_activity", "residence"],)
        assert worker in worker.residence.people
        assert pupil in pupil.residence.people
        pupil.health_information = None
        sim.clear_world()


class TestClosure:
    def test__close_schools(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        household = Household()
        household.add(pupil, subgroup_type=household.SubgroupType.kids)
        household.add(worker, subgroup_type=household.SubgroupType.adults)
        school_closure = CloseSchools(
            start_time="2020-1-1", end_time="2020-10-1", years_to_close=[6],
        )
        policies = Policies([school_closure])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        # non key worker
        worker.lockdown_status = "furlough"
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.skip_activity_collection(date=time_during_policy)(
            pupil, activities
        ) == ["residence"]
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert pupil in pupil.residence.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.skip_activity_collection(date=time_after_policy)(
            pupil, activities
        ) == ["primary_activity", "residence",]
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

        #key worker
        worker.lockdown_status = "key_worker"
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.skip_activity_collection(date=time_during_policy)(
            pupil, activities
        ) == ["primary_activity", "residence"]
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.skip_activity_collection(date=time_after_policy)(
            pupil, activities
        ) == ["primary_activity", "residence",]
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()


    def test__close_universities(self, super_area, selector, interaction):
        pupil, student, world = make_dummy_world_with_university(super_area)
        university_closure = CloseUniversities(
            start_time="2020-1-1", end_time="2020-10-1",
        )
        policies = Policies([university_closure])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
        sim.clear_world()
        activities = ["primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert student in student.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.skip_activity_collection(date=time_during_policy)(
            student, activities
        ) == ["residence"]
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert student in student.residence.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.skip_activity_collection(date=time_after_policy)(
            student, activities
        ) == ["primary_activity", "residence",]
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert student in student.primary_activity.people
        sim.clear_world()

    def test__close_companies(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        company_closure = CloseCompanies(
            start_time="2020-1-1", end_time="2020-10-1"
        )
        policies = Policies([company_closure])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        #sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "furlough"
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.skip_activity_collection(date=time_during_policy)(
            worker, activities
        ) == ["residence"]
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.skip_activity_collection(date=time_after_policy)(
            worker, activities
        ) == ["commute", "primary_activity", "residence",]
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

        # no furlough
        sim.clear_world()
        activities = ["commute", "primary_activity", "residence"]
        time_before_policy = datetime(2019, 2, 1)
        worker.lockdown_status = "key_worker"
        sim.move_people_to_active_subgroups(activities, time_before_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.skip_activity_collection(date=time_during_policy)(
            worker, activities
        ) == ["commute", "primary_activity", "residence"]
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.primary_activity.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()
        time_after_policy = datetime(2030, 2, 2)
        assert policies.skip_activity_collection(date=time_after_policy)(
            worker, activities
        ) == ["commute", "primary_activity", "residence",]
        sim.move_people_to_active_subgroups(activities, time_after_policy)
        assert pupil in pupil.primary_activity.people
        assert worker in worker.primary_activity.people
        sim.clear_world()

    def test__close_companies_full_closure(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        company_closure = CloseCompanies(
            start_time="2020-1-1", end_time="2020-10-1", full_closure=True,
        )
        policies = Policies([company_closure])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        worker.lockdown_status = "key_worker"
        activities = ["commute", "primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.skip_activity_collection(date=time_during_policy)(
            worker, activities
        ) == ["residence"]
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.residence.people
        sim.clear_world()


class TestShielding:
    def test__old_people_shield(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        shielding = Shielding(start_time="2020-1-1", end_time="2020-10-1", min_age=30)
        policies = Policies([shielding])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 2, 1)
        assert policies.stay_home_collection(date=time_during_policy)(
            worker, activities
        )
        sim.move_people_to_active_subgroups(activities, time_during_policy)
        assert worker in worker.residence.people
        assert pupil in pupil.primary_activity.people
        sim.clear_world()


class TestQuarantine:
    def test__symptomatic_stays_for_one_week(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        quarantine = Quarantine(
            start_time="2020-1-1", end_time="2020-1-30", n_days=7, n_days_household=14,
        )
        policies = Policies([quarantine])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        assert policies.stay_home_collection(date=time_during_policy)(worker, 6.0)
        sim.move_people_to_active_subgroups(activities, time_during_policy, 6.0)
        assert worker in worker.residence.people
        worker.health_information = None
        sim.clear_world()

    def test__housemates_stay_for_two_weeks(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        quarantine = Quarantine(
            start_time="2020-1-1", end_time="2020-1-30", n_days=7, n_days_household=14,
        )
        policies = Policies([quarantine])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        infect_person(worker, selector, "influenza")
        sim.update_health_status(0.0, 0.0)
        activities = ["primary_activity", "residence"]
        sim.clear_world()
        time_during_policy = datetime(2020, 1, 2)
        # before symptoms onset
        assert not policies.stay_home_collection(date=time_during_policy)(pupil, 4.0)
        # after symptoms onset
        assert policies.stay_home_collection(date=time_during_policy)(pupil, 8.0)
        sim.move_people_to_active_subgroups(activities, time_during_policy, 8.0)
        assert pupil in pupil.residence.people
        # more thatn two weeks after symptoms onset
        assert not policies.stay_home_collection(date=time_during_policy)(pupil, 25.0)
        worker.health_information = None
        sim.clear_world()


class TestCloseLeisure:
    def test__close_leisure_venues(self, super_area, selector, interaction):
        pupil, worker, world = make_dummy_world(super_area)
        close_venues = CloseLeisureVenue(
            start_time="2020-3-1", end_time="2020-3-30", venues_to_close=["pub"],
        )
        policies = Policies([close_venues])
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        sim.leisure.leisure_distributors["pubs"].weekend_boost = 5000
        sim.clear_world()
        time_before_policy = datetime(2019, 2, 1)
        activities = ["leisure", "residence"]
        sim.leisure.generate_leisure_probabilities_for_timestep(10000, False, [])
        sim.move_people_to_active_subgroups(
            activities, time_before_policy, 0.0
        )
        assert worker in worker.leisure.people
        sim.clear_world()
        time_during_policy = datetime(2020, 3, 14)
        closed_venues = policies.find_closed_venues(date=time_during_policy)
        assert list(closed_venues) == ["pub"]
        sim.leisure.generate_leisure_probabilities_for_timestep(10000, False, closed_venues) 
        sim.move_people_to_active_subgroups(
            activities, time_during_policy, 0.0
        )
        assert (
            worker in worker.leisure.people and worker.leisure.group.spec == "cinema"
        ) or worker in worker.residence.people
        sim.clear_world()


def test__social_distancing(super_area, selector, interaction):
    pupil, worker, world = make_dummy_world(super_area)
    world.cemeteries = Cemeteries()
    start_date = datetime(2020, 3, 10)
    end_date = datetime(2020, 3, 12)
    beta_factor = {
        "box": 0.5,
        "pub": 0.5,
        "grocery": 0.5,
        "cinema": 0.5,
        "commute_unit": 0.5,
        "commute_city_unit": 0.5,
        "hospital": 0.5,
        "care_home": 0.5,
        "company": 0.5,
        "school": 0.5,
        "household": 1.0,
        "university": 0.5,
    }

    social_distance = SocialDistancing(
        start_time="2020-03-10", end_time="2020-03-12", beta_factor=beta_factor
    )
    policies = Policies([social_distance])
    leisure_instance = leisure.generate_leisure_for_config(
        world=world, config_filename=test_config
    )
    sim = Simulator.from_file(
        world,
        interaction,
        selector,
        config_filename=test_config,
        policies=policies,
        leisure=leisure_instance,
    )

    sim.timer.reset()

    initial_betas = copy.deepcopy(sim.interaction.beta)
    sim.clear_world()
    for time in sim.timer:
        if time > sim.timer.final_date:
            break
        sim.do_timestep()
        if sim.timer.date >= start_date and sim.timer.date < end_date:
            for group in sim.interaction.beta:
                if group != "household":
                    assert sim.interaction.beta[group] == initial_betas[group] * 0.5
                else:
                    assert sim.interaction.beta[group] == initial_betas[group]
        else:
            assert sim.interaction.beta == initial_betas


class TestReduceLeisureProbabilities:
    def test__reduce_household_visits(self, super_area, selector, interaction):
        _, _, world = make_dummy_world(super_area)
        leisure_instance = leisure.generate_leisure_for_config(
            world=world, config_filename=test_config
        )
        reduce_leisure_probabilities = ChangeLeisureProbability(
            start_time="2020-03-02",
            end_time="2020-03-05",
            leisure_activities_probabilities={
                "pubs": {"men": {"0-50": 0.5, "50-100": 0.0}, "women": {"0-100": 0.4},},
            },
        )
        policies = Policies([reduce_leisure_probabilities])
        sim = Simulator.from_file(
            world,
            interaction,
            selector,
            config_filename=test_config,
            policies=policies,
            leisure=leisure_instance,
        )
        sim.clear_world()
        sim.policies.apply_change_probabilities_leisure(sim.timer.date, sim.leisure)
        sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
        original_male_pub_probabilities = sim.leisure.leisure_distributors[
            "pubs"
        ].male_probabilities
        original_female_pub_probabilities = sim.leisure.leisure_distributors[
            "pubs"
        ].female_probabilities
        assert str(sim.timer.date.date()) == "2020-03-01"
        household = Household()
        person1 = Person.from_attributes(age=60, sex="m")
        person1.area = super_area.areas[0]
        household.add(person1)
        person2 = Person.from_attributes(age=80, sex="f")
        person2.area = super_area.areas[0]
        sim.leisure.distribute_social_venues_to_people([person1, person2])
        household.add(person2)
        pubs1_visits_before = 0
        pubs2_visits_before = 0
        for _ in range(5000):
            subgroup = sim.leisure.get_subgroup_for_person_and_housemates(person1)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_before += 1
            person1.subgroups.leisure = None
            subgroup = sim.leisure.get_subgroup_for_person_and_housemates(person2)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_before += 1
            person2.subgroups.leisure = None
        assert pubs1_visits_before > 0
        assert pubs2_visits_before > 0
        # next day leisure policies are
        while str(sim.timer.date.date()) != "2020-03-02":
            next(sim.timer)
        sim.policies.apply_change_probabilities_leisure(sim.timer.date, sim.leisure)
        sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
        assert sim.leisure.leisure_distributors["pubs"].male_probabilities[60] == 0.0
        assert sim.leisure.leisure_distributors["pubs"].female_probabilities[60] == 0.4
        pubs1_visits_after = 0
        pubs2_visits_after = 0
        for _ in range(5000):
            subgroup = sim.leisure.get_subgroup_for_person_and_housemates(person1)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_after += 1
            person1.subgroups.leisure = None
            subgroup = sim.leisure.get_subgroup_for_person_and_housemates(person2)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_after += 1
            person2.subgroups.leisure = None
        assert pubs1_visits_after == 0
        assert 0 < pubs2_visits_after < pubs2_visits_before
        # end of policy
        while str(sim.timer.date.date()) != "2020-03-05":
            next(sim.timer)
        sim.policies.apply_change_probabilities_leisure(sim.timer.date, sim.leisure)
        sim.leisure.generate_leisure_probabilities_for_timestep(0.1, False, [])
        pubs1_visits_restored = 0
        pubs2_visits_restored = 0
        for _ in range(5000):
            subgroup = sim.leisure.get_subgroup_for_person_and_housemates(person1)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs1_visits_restored += 1
            person1.subgroups.leisure = None
            subgroup = sim.leisure.get_subgroup_for_person_and_housemates(person2)
            if subgroup is not None and subgroup.group.spec == "pub":
                pubs2_visits_restored += 1
            person2.subgroups.leisure = None
        assert np.isclose(pubs1_visits_restored, pubs1_visits_before, rtol=0.1)
        assert np.isclose(pubs2_visits_restored, pubs2_visits_before, rtol=0.1)
        assert (
            sim.leisure.leisure_distributors["pubs"].male_probabilities
            == original_male_pub_probabilities
        )
        assert (
            sim.leisure.leisure_distributors["pubs"].female_probabilities
            == original_female_pub_probabilities
        )


"""
class TestSocialDistancing:
    def test__social_distancing(self, selector):
        beta_factor = {
                    'box': 0.5,
                    'pub': 0.5,
                    'grocery': 0.5,
                    'cinema': 0.5,
                    'commute_unit': 0.5,
                    'commute_city_unit': 0.5,
                    'hospital': 0.5,
                    'care_home': 0.5,
                    'company': 0.5,
                    'school': 0.5,
                    'university': 0.5,
                }
        social_distance = SocialDistancing(start_time='2020-03-10', end_time='2020-03-12',
            beta_factor = beta_factor)
        interaction = ContactAveraging.from_file(selector=selector,
                policies=Policies([social_distance]))
        initial_betas = interaction.beta
        for group in interaction.beta.keys():
            if group in social_distance.beta_factor.keys(): 
                assert interaction.beta[group]*interaction.policies.get_beta_factors(group) == initial_betas[group] * 0.5
            else:
                assert interaction.beta[group]*interaction.policies.social_distance_beta_factor(group) == initial_betas[group]
"""
