from pathlib import Path

import random
import tables
import numpy as np
import pytest
import pandas as pd

from june import paths
from june.demography import Person, Population
from june.demography import Geography
from june.groups import Hospital, School, Company, Household, University
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    Universities,
    Cemeteries,
)
from june.infection import SymptomTag
from june.interaction import Interaction
from june.infection.infection_selector import InfectionSelector
from june.infection_seed import InfectionSeed
from june.policy import (
    Policies,
    Hospitalisation
)
from june.simulator import Simulator
from june.world import World
from june.records import Record, RecordReader

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
test_config = paths.configs_path / "tests/test_simulator_no_leisure.yaml"


def clean_world(world):
    for person in world.people:
        person.infection = None
        person.susceptibility = 1.0

class MockHealthIndexGenerator:
    def __init__(self, desired_symptoms):
        self.index = desired_symptoms

    def __call__(self, person):
        hi = np.ones(8)
        for h in range(len(hi)):
            if h < self.index:
                hi[h] = 0
        return hi


def make_selector(desired_symptoms,):
    health_index_generator = MockHealthIndexGenerator(desired_symptoms)
    selector = InfectionSelector.from_file(
        health_index_generator=health_index_generator,
    )
    return selector


def infect_hospitalised_person(person):
    max_symptom_tag = random.choice(
        [SymptomTag.hospitalised, SymptomTag.intensive_care,]
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
def create_selector():
    selector = InfectionSelector.from_file(
        paths.configs_path / "defaults/transmission/XNExp.yaml"
    )
    selector.recovery_rate = 1.0
    selector.transmission_probability = 1.0
    return selector


@pytest.fixture(name="interaction", scope="module")
def create_interaction():
    interaction = Interaction.from_file()
    interaction.beta["school"] = 0.8
    interaction.beta["cinema"] = 0.0
    interaction.beta["pub"] = 0.0
    interaction.beta["household"] = 10.0
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
    household1.id = 1992
    household1.area = super_area.areas[0]
    hospital = Hospital(
        n_beds=40,
        n_icu_beds=5,
        area=geog.areas.members[0],
        coordinates=super_area.coordinates,
    )
    uni = University(coordinates=super_area.coordinates, n_students_max=2500,)

    worker1 = Person.from_attributes(age=44, sex="f", ethnicity="A1", socioecon_index=5)
    worker1.area = super_area.areas[0]
    household1.add(worker1, subgroup_type=household1.SubgroupType.adults)
    worker1.sector = "Q"
    company.add(worker1)

    worker2 = Person.from_attributes(age=42, sex="m", ethnicity="B1", socioecon_index=5)
    worker2.area = super_area.areas[0]
    household1.add(worker2, subgroup_type=household1.SubgroupType.adults)
    worker2.sector = "Q"
    company.add(worker2)

    student1 = Person.from_attributes(
        age=20, sex="f", ethnicity="A1", socioecon_index=5
    )
    student1.area = super_area.areas[0]
    household1.add(student1, subgroup_type=household1.SubgroupType.adults)
    uni.add(student1)

    pupil1 = Person.from_attributes(age=8, sex="m", ethnicity="C1", socioecon_index=5)
    pupil1.area = super_area.areas[0]
    household1.add(pupil1, subgroup_type=household1.SubgroupType.kids)
    # school.add(pupil1)

    pupil2 = Person.from_attributes(age=5, sex="f", ethnicity="A1", socioecon_index=5)
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
    return world


def create_sim(world, interaction, selector, seed=False):

    record = Record.from_world(record_path="results", filename="test.hdf5", world=world)
    policies = Policies(
            [Hospitalisation(start_time='1000-01-01',
                end_time='9999-01-01')]
    )
    infection_seed = InfectionSeed(super_areas=world.super_areas, selector=selector)
    if not seed:
        n_cases = 2
        infection_seed.unleash_virus(n_cases, record=record)
    elif seed == 'hospitalised':
        for person in world.people:
            infect_hospitalised_person(person)
    else:
        for person in world.people:
            infect_dead_person(person)

    sim = Simulator.from_file(
        world=world,
        interaction=interaction,
        infection_selector=selector,
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
    assert read.run_summary.iloc[0]['daily_infections_by_residence'] == 2 # seed
    for key in list(new_infected.keys())[1:]:
        if new_infected[key]:
            assert read.run_summary.loc[key, 'daily_infections_by_residence'] == len(new_infected[key])

def test__log_hospital_admissions(world, interaction, selector):
    clean_world(world)
    sim = create_sim(world, interaction, selector, seed='hospitalised')
    sim.timer.reset()
    counter = 0
    saved_ids = []
    hospital_admissions = {}
    while counter < 10:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_hosps_ids = []
        sim.update_health_status(sim.timer.now, sim.timer.duration)
        for person in world.people.infected:
            if person.medical_facility is not None and person.id not in saved_ids:
                daily_hosps_ids.append(person.id)
                saved_ids.append(person.id)
        hospital_admissions[timer] = daily_hosps_ids
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    read = RecordReader(results_path=sim.record.record_path)
    assert read.run_summary.iloc[0]['daily_infections_by_residence'] == 2 # seed
    for key in list(hospital_admissions.keys())[1:]:
        if hospital_admissions[key]:
            assert read.run_summary.loc[key, 'daily_hospital_admissions'] == len(hospital_admissions[key])


'''
def test__log_deaths(world, interaction, selector):
    clean_world(world)
    sim = create_sim(world, interaction, selector, seed='dead')
    sim.timer.reset()
    counter = 0
    saved_ids = []
    deaths = {}
    while counter < 50:
        timer = sim.timer.date.strftime("%Y-%m-%d")
        daily_deaths_ids = []
        sim.update_health_status(sim.timer.now, sim.timer.duration)
        for person in world.people:
            if person.dead and person.id not in saved_ids:
                daily_deaths_ids.append(person.id)
                saved_ids.append(person.id)
        deaths[timer] = daily_deaths_ids 
        sim.record.time_step(timestamp=sim.timer.date)
        next(sim.timer)
        counter += 1
    sim.record.file = tables.open_file(
        sim.record.record_path / sim.record.filename, mode="r"
    )
    table = sim.record.file.root.deaths
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
    sim.record.file.close()
    clean_world(world)
'''
