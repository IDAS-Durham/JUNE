from pathlib import Path
from collections import defaultdict

import random
import tables
import numpy as np
import pytest
import pandas as pd

from june import paths
from june.demography import Person, Population, Activities
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
from june.epidemiology.infection import (
    SymptomTag,
    Immunity,
    InfectionSelectors,
    InfectionSelector,
)
from june.interaction import Interaction
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection_seed import InfectionSeed
from june.policy import Policies, Hospitalisation
from june.simulator import Simulator
from june.world import World
from june.records import Record

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent

test_config = paths.configs_path / "tests/test_simulator_no_leisure.yaml"
interaction_config = paths.configs_path / "tests/interaction.yaml"


def clean_world(world):
    for person in world.people:
        person.infection = None
        person.dead = False
        person.immunity = Immunity()
        person.subgroups.medical_facility = None
    for hospital in world.hospitals:
        hospital.ward_ids = set()
        hospital.icu_ids = set()


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
        infection_seed.unleash_virus_per_day(
            time=0.0, date=pd.to_datetime("2020-03-01"), record=record
        )
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


def test__log_infected(world, interaction, selector):
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

    with tables.open_file(sim.record.record_path / sim.record.filename, mode="r") as f:
        table = f.root.infections
        df = pd.DataFrame.from_records(table.read())
    df["timestamp"] = df["timestamp"].str.decode("utf-8")
    df["location_specs"] = df["location_specs"].str.decode("utf-8")
    df.set_index("timestamp", inplace=True)
    assert set(df.loc["2020-03-01"]["infector_ids"].values) == set(infections_seed)
    assert set(df.loc["2020-03-01"]["infected_ids"].values) == set(infections_seed)
    assert set(df.loc["2020-03-01"]["location_ids"].values) == set([0, 0])
    assert set(df.loc["2020-03-01"]["location_specs"].values) == set(
        ["infection_seed", "infection_seed"]
    )
    for timestamp in list(new_infected.keys())[1:]:
        if new_infected[timestamp]:
            if type(df.loc[timestamp]["infected_ids"]) is np.int32:
                assert df.loc[timestamp]["infected_ids"] == new_infected[timestamp]
                assert df.loc[timestamp]["infector_ids"] != new_infected[timestamp]
            else:
                assert set(df.loc[timestamp]["infected_ids"].values) == set(
                    new_infected[timestamp]
                )
    df.iloc[2:]["location_ids"].values == [world.households[0].id] * len(df.iloc[2:])
    df.iloc[2:]["location_specs"].values == ["household"] * len(df.iloc[2:])


def test__log_hospital_admissions(world, interaction, selector):
    clean_world(world)
    sim = create_sim(world, interaction, selector, seed="hospitalised")
    sim.timer.reset()
    counter = 0
    saved_ids, discharged_ids = [], []
    hospital_admissions, hospital_discharges = {}, {}
    while counter < 50:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_hosps_ids, daily_discharges_ids = [], []
        sim.epidemiology.update_health_status(
            sim.world, sim.timer.now, sim.timer.duration, record=sim.record
        )
        for person in world.people.infected:
            if person.medical_facility is not None and person.id not in saved_ids:
                daily_hosps_ids.append(person.id)
                saved_ids.append(person.id)
        for person in world.people:
            if (
                person.medical_facility is None
                and person.id in saved_ids
                and person.id not in discharged_ids
            ):
                daily_discharges_ids.append(person.id)
                discharged_ids.append(person.id)
        hospital_admissions[timer] = daily_hosps_ids
        hospital_discharges[timer] = daily_discharges_ids
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    with tables.open_file(sim.record.record_path / sim.record.filename, mode="r") as f:
        table = f.root.hospital_admissions
        admissions_df = pd.DataFrame.from_records(table.read())
        table = f.root.discharges
        discharges_df = pd.DataFrame.from_records(table.read())
    admissions_df["timestamp"] = admissions_df["timestamp"].str.decode("utf-8")
    admissions_df.set_index("timestamp", inplace=True)
    discharges_df["timestamp"] = discharges_df["timestamp"].str.decode("utf-8")
    discharges_df.set_index("timestamp", inplace=True)

    for timestamp in hospital_admissions.keys():
        if hospital_admissions[timestamp]:
            if type(admissions_df.loc[timestamp]["patient_ids"]) is np.int32:
                assert (
                    admissions_df.loc[timestamp]["patient_ids"]
                    == hospital_admissions[timestamp]
                )
            else:
                assert set(admissions_df.loc[timestamp]["patient_ids"].values) == set(
                    hospital_admissions[timestamp]
                )
        if hospital_discharges[timestamp]:
            if type(discharges_df.loc[timestamp]["patient_ids"]) is np.int32:
                assert (
                    discharges_df.loc[timestamp]["patient_ids"]
                    == hospital_discharges[timestamp]
                )
            else:
                assert set(discharges_df.loc[timestamp]["patient_ids"].values) == set(
                    hospital_admissions[timestamp]
                )
    clean_world(world)


def test__log_icu_admissions(world, interaction, selector):
    clean_world(world)
    sim = create_sim(world, interaction, selector, seed="hospitalised")
    sim.timer.reset()
    counter = 0
    saved_ids = []
    icu_admissions = {}
    while counter < 50:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_icu_ids = []
        sim.epidemiology.update_health_status(
            sim.world, sim.timer.now, sim.timer.duration, record=sim.record
        )
        for person in world.people.infected:
            if (
                person.infection.symptoms.tag == SymptomTag.intensive_care
                and person.id not in saved_ids
            ):
                daily_icu_ids.append(person.id)
                saved_ids.append(person.id)
        icu_admissions[timer] = daily_icu_ids
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    with tables.open_file(sim.record.record_path / sim.record.filename, mode="r") as f:
        table = f.root.icu_admissions
        admissions_df = pd.DataFrame.from_records(table.read())
    admissions_df["timestamp"] = admissions_df["timestamp"].str.decode("utf-8")
    admissions_df.set_index("timestamp", inplace=True)
    for timestamp in icu_admissions.keys():
        if icu_admissions[timestamp]:
            if type(admissions_df.loc[timestamp]["patient_ids"]) is np.int32:
                assert (
                    admissions_df.loc[timestamp]["patient_ids"]
                    == icu_admissions[timestamp]
                )
            else:
                assert set(admissions_df.loc[timestamp]["patient_ids"].values) == set(
                    icu_admissions[timestamp]
                )
    clean_world(world)


def test__symptoms_transition(world, interaction, selector):
    sim = create_sim(world, interaction, selector, seed="dead")
    sim.timer.reset()
    counter = 0
    ids_transition, symptoms_transition = {}, {}
    symptoms = defaultdict(int)
    while counter < 20:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_transitions_ids, daily_transitions_symptoms = [], []
        sim.epidemiology.update_health_status(
            sim.world, sim.timer.now, sim.timer.duration, record=sim.record
        )
        for person in world.people.infected:
            symptoms_tag = person.infection.symptoms.tag.value
            if symptoms_tag != symptoms[person.id]:
                daily_transitions_ids.append(person.id)
                daily_transitions_symptoms.append(symptoms_tag)
            symptoms[person.id] = symptoms_tag
        ids_transition[timer] = daily_transitions_ids
        symptoms_transition[timer] = daily_transitions_symptoms
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    with tables.open_file(sim.record.record_path / sim.record.filename, mode="r") as f:
        table = f.root.symptoms
        df = pd.DataFrame.from_records(table.read())
    df["timestamp"] = df["timestamp"].str.decode("utf-8")
    df.set_index("timestamp", inplace=True)
    df = df.loc[~df.new_symptoms.isin([5, 6, 7])]
    for timestamp in list(ids_transition.keys())[1:]:
        if ids_transition[timestamp]:
            if type(df.loc[timestamp]["infected_ids"]) is np.int32:
                assert df.loc[timestamp]["infected_ids"] == ids_transition[timestamp]
                assert (
                    df.loc[timestamp]["new_symptoms"] == symptoms_transition[timestamp]
                )
            else:
                assert set(df.loc[timestamp]["infected_ids"].values) == set(
                    ids_transition[timestamp]
                )
                assert set(df.loc[timestamp]["new_symptoms"].values) == set(
                    symptoms_transition[timestamp]
                )

    clean_world(world)


def test__log_deaths(world, interaction, selector):
    for person in world.people:
        person.subgroups = Activities(
            world.households[0].subgroups[0], None, None, None, None, None
        )
    sim = create_sim(world, interaction, selector, seed="dead")
    sim.timer.reset()
    counter = 0
    saved_ids = []
    deaths = {}
    while counter < 50:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_deaths_ids = []
        sim.epidemiology.update_health_status(
            sim.world,
            sim.timer.now,
            sim.timer.duration,
            record=sim.record,
        )
        for person in world.people:
            if person.dead and person.id not in saved_ids:
                daily_deaths_ids.append(person.id)
                saved_ids.append(person.id)
        deaths[timer] = daily_deaths_ids
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    with tables.open_file(sim.record.record_path / sim.record.filename, mode="r") as f:
        table = f.root.deaths
        df = pd.DataFrame.from_records(table.read())
    df["timestamp"] = df["timestamp"].str.decode("utf-8")
    df.set_index("timestamp", inplace=True)
    for timestamp in deaths.keys():
        if deaths[timestamp]:
            if type(df.loc[timestamp]["dead_person_ids"]) is np.int32:
                assert df.loc[timestamp]["dead_person_ids"] == deaths[timestamp]
            else:
                assert set(df.loc[timestamp]["dead_person_ids"].values) == set(
                    deaths[timestamp]
                )
    clean_world(world)
