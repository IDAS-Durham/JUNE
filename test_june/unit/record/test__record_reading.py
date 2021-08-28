from pathlib import Path

import random
import tables
import numpy as np
import pytest
import pandas as pd
from june import paths
from june.demography import Person, Population
from june.geography import Geography
from june.groups import Hospital, School, Company, Household, University
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
)
from june.interaction import Interaction
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection import (
    InfectionSelector,
    InfectionSelectors,
    SymptomTag,
    Immunity,
)
from june.epidemiology.infection_seed import InfectionSeed
from june.policy import Policies, Hospitalisation
from june.simulator import Simulator
from june.world import World
from june.records import Record, RecordReader

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
test_config = paths.configs_path / "tests/test_simulator_no_leisure.yaml"
interaction_config = paths.configs_path / "tests/interaction.yaml"


def clean_world(world):
    for person in world.people:
        person.infection = None
        person.immunity = Immunity()


class MockHealthIndexGenerator:
    def __init__(self, desired_symptoms):
        self.index = desired_symptoms

    def __call__(self, person, infection_id):
        hi = np.ones(8)
        for h in range(len(hi)):
            if h < self.index:
                hi[h] = 0
        return hi


def make_selector(
    desired_symptoms,
):
    health_index_generator = MockHealthIndexGenerator(desired_symptoms)
    selector = InfectionSelector(
        health_index_generator=health_index_generator,
    )
    return selector


def infect_hospitalised_person(person):
    max_symptom_tag = random.choice(
        [
            SymptomTag.hospitalised,
            SymptomTag.intensive_care,
        ]
    )
    selector = make_selector(desired_symptoms=max_symptom_tag)
    selector.infect_person_at_time(person, 0.0)


def infect_dead_person(person):
    max_symptom_tag = random.choice(
        [SymptomTag.dead_home, SymptomTag.dead_hospital, SymptomTag.dead_icu]
    )
    selector = make_selector(desired_symptoms=max_symptom_tag)
    selector.infect_person_at_time(person, 0.0)


@pytest.fixture(name="selector", scope="module")
def create_selector(health_index_generator):
    selector = InfectionSelector(
        paths.configs_path / "defaults/epidemiology/infection/transmission/XNExp.yaml",
        health_index_generator=health_index_generator,
    )
    selector.recovery_rate = 1.0
    selector.transmission_probability = 1.0
    return selector


@pytest.fixture(name="interaction", scope="module")
def create_interaction():
    interaction = Interaction.from_file(config_filename=interaction_config)
    interaction.betas["school"] = 0.8
    interaction.betas["cinema"] = 0.0
    interaction.betas["pub"] = 0.0
    interaction.betas["household"] = 10.0
    interaction.alpha_physical = 2.7
    return interaction


@pytest.fixture(name="geog", scope="module")
def create_geography():
    geog = Geography.from_file(filter_key={"area": ["E00000001"]})
    return geog


@pytest.fixture(name="world", scope="module")
def make_dummy_world(geog):
    super_area = geog.super_areas.members[0]
    company = Company(super_area=super_area, n_workers_max=100, sector="Q")

    household1 = Household()
    household1.area = super_area.areas[0]
    hospital = Hospital(
        n_beds=40,
        n_icu_beds=5,
        area=geog.areas.members[0],
        coordinates=super_area.coordinates,
    )
    uni = University(
        coordinates=super_area.coordinates,
        n_students_max=2500,
    )

    worker1 = Person.from_attributes(age=44, sex="f", ethnicity="A1")
    worker1.area = super_area.areas[0]
    household1.add(worker1, subgroup_type=household1.SubgroupType.adults)
    worker1.sector = "Q"
    company.add(worker1)

    worker2 = Person.from_attributes(age=42, sex="m", ethnicity="B1")
    worker2.area = super_area.areas[0]
    household1.add(worker2, subgroup_type=household1.SubgroupType.adults)
    worker2.sector = "Q"
    company.add(worker2)

    student1 = Person.from_attributes(age=20, sex="f", ethnicity="A1")
    student1.area = super_area.areas[0]
    household1.add(student1, subgroup_type=household1.SubgroupType.adults)
    uni.add(student1)

    pupil1 = Person.from_attributes(age=8, sex="m", ethnicity="C1")
    pupil1.area = super_area.areas[0]
    household1.add(pupil1, subgroup_type=household1.SubgroupType.kids)
    # school.add(pupil1)

    pupil2 = Person.from_attributes(age=5, sex="f", ethnicity="A1")
    pupil2.area = super_area.areas[0]
    household1.add(pupil2, subgroup_type=household1.SubgroupType.kids)
    # school.add(pupil2)

    world = World()
    world.schools = Schools([School()])
    world.hospitals = Hospitals([hospital])
    world.households = Households([household1])
    world.universities = Universities([uni])
    world.companies = Companies([company])
    world.people = Population([worker1, worker2, student1, pupil1, pupil2])
    world.regions = geog.regions
    world.super_areas = geog.super_areas
    world.areas = geog.areas
    world.cemeteries = Cemeteries()
    world.areas[0].people = world.people
    world.super_areas[0].closest_hospitals = [world.hospitals[0]]
    return world


def create_sim(world, interaction, selector, seed=False):
    record = Record(record_path="results")
    policies = Policies(
        [Hospitalisation(start_time="1000-01-01", end_time="9999-01-01")]
    )
    infection_seed = InfectionSeed.from_uniform_cases(
        world=world,
        infection_selector=selector,
        cases_per_capita=2 / len(world.people),
        date="2020-03-01",
    )
    if not seed:
        infection_seed.unleash_virus_per_day(date=pd.to_datetime("2020-03-01"), time=0, record=record)
    elif seed == "hospitalised":
        for person in world.people:
            infect_hospitalised_person(person)
    else:
        for person in world.people:
            infect_dead_person(person)

    selectors = InfectionSelectors([selector])
    epidemiology = Epidemiology(infection_selectors=selectors)
    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        epidemiology=epidemiology,
        config_filename=test_config,
        policies=policies,
        record=record,
    )
    return sim


def test__log_infected_by_region(world, interaction, selector):
    clean_world(world)
    sim = create_sim(world, interaction, selector)
    infections_seed = [person.id for person in world.people.infected]
    sim.timer.reset()
    counter = 0
    new_infected = {}
    already_infected = [person.id for person in world.people.infected]
    while counter < 10:
        time = sim.timer.date.strftime("%Y-%m-%d")
        sim.do_timestep()
        current_infected = [
            person.id
            for person in world.people.infected
            if person.id not in already_infected
        ]
        new_infected[time] = current_infected
        next(sim.timer)
        counter += 1
        already_infected += current_infected
    read = RecordReader(results_path=sim.record.record_path)
    assert read.regional_summary.iloc[0]["daily_infected"] == 2  # seed
    for key in list(new_infected.keys())[1:]:
        if new_infected[key]:
            assert read.regional_summary.loc[key, "daily_infected"] == len(
                new_infected[key]
            )


def test__log_hospital_admissions(world, interaction, selector):
    clean_world(world)
    sim = create_sim(world, interaction, selector, seed="hospitalised")
    sim.timer.reset()
    counter = 0
    saved_ids = []
    hospital_admissions = {}
    while counter < 15:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_hosps_ids = []
        sim.epidemiology.update_health_status(
            sim.world, sim.timer.now, sim.timer.duration, sim.record
        )
        for person in world.people.infected:
            if person.medical_facility is not None and person.id not in saved_ids:
                daily_hosps_ids.append(person.id)
                saved_ids.append(person.id)
        hospital_admissions[timer] = daily_hosps_ids
        sim.record.summarise_time_step(timestamp=sim.timer.date, world=sim.world)
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    read = RecordReader(results_path=sim.record.record_path)
    for key in list(hospital_admissions.keys()):
        if hospital_admissions[key]:
            assert read.regional_summary.loc[key, "daily_hospitalised"] == len(
                hospital_admissions[key]
            )
            assert read.world_summary.loc[key, "daily_hospitalised"] == len(
                hospital_admissions[key]
            )
    clean_world(world)


def test__log_deaths(world, interaction, selector):
    sim = create_sim(world, interaction, selector, seed="dead")
    sim.timer.reset()
    counter = 0
    saved_ids = []
    deaths = {}
    while counter < 50:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_deaths_ids = []
        sim.epidemiology.update_health_status(
            sim.world, sim.timer.now, sim.timer.duration, sim.record
        )
        for person in world.people:
            if person.dead and person.id not in saved_ids:
                daily_deaths_ids.append(person.id)
                saved_ids.append(person.id)
        deaths[timer] = daily_deaths_ids
        sim.record.summarise_time_step(timestamp=sim.timer.date, world=sim.world)
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    read = RecordReader(results_path=sim.record.record_path)
    for key in list(deaths.keys()):
        if deaths[key]:
            assert read.regional_summary.loc[key, "daily_deaths"] == len(deaths[key])
    clean_world(world)
