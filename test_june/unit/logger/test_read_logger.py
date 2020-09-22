from collections import defaultdict
import pandas as pd
import numpy as np
import random
from june.infection import Infection, InfectionSelector
from june.infection import SymptomTag
from june.logger import Logger, ReadLogger
from june.world import World
from june.demography import Person, Population
from june.time import Timer


class MockSuperArea:
    def __init__(self):
        self.name = "holi"


class MockArea:
    def __init__(self):
        self.super_area = MockSuperArea()


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
        [SymptomTag.dead_home, SymptomTag.dead_icu, SymptomTag.dead_hospital]
    )
    selector = make_selector(desired_symptoms=max_symptom_tag)
    selector.infect_person_at_time(person, 0.0)


def make_dummy_world(infected):
    world = World()
    people = []
    for i in range(20):
        person = Person.from_attributes(
            age=40, sex="f", ethnicity="guapo", socioecon_index=0
        )
        person.area = MockArea()
        if infected:
            infect_hospitalised_person(person)
        people.append(person)
    world.people = Population(people)
    return world


def test__read_daily_hospital_admissions():
    world = make_dummy_world(infected=True)
    output_path = "dummy_results"
    logger = Logger(save_path=output_path)
    timer = Timer(initial_day="2020-03-10", total_days=15)
    saved_ids = []
    hospital_admissions = defaultdict(int)
    logger.log_population(world.people)
    while timer.date <= timer.final_date:
        time = timer.date
        ids = []
        symptoms = []
        for person in world.people.infected:
            new_status = person.infection.update_health_status(
                timer.now, timer.duration
            )
            ids.append(person.id)
            symptoms.append(person.infection.tag.value)
            if (
                person.infection.symptoms.tag == SymptomTag.hospitalised
                and person.id not in saved_ids
            ):
                saved_ids.append(person.id)
                hospital_admissions[time.strftime("%Y-%m-%dT%H:%M:%S.%f")] += 1

            if new_status == "recovered":
                person.infection = None
        n_secondary_infections = [0] * len(ids)
        super_area_infections = {
            "holi": {
                "ids": ids,
                "symptoms": symptoms,
                "n_secondary_infections": n_secondary_infections,
            }
        }
        logger.log_infected(timer.date, super_area_infections)
        logger.log_infection_location(time)
        next(timer)
    read = ReadLogger(output_path=output_path)
    world_df = read.world_summary()
    # Test hospital admissions are right
    hospital_admissions_df = pd.Series(hospital_admissions)
    hospital_admissions_df.index = pd.to_datetime(hospital_admissions_df.index)
    hospital_admissions_logged = world_df["daily_hospital_admissions"]
    hospital_admissions_logged = hospital_admissions_logged[
        hospital_admissions_logged.values > 0
    ]
    assert sum(list(hospital_admissions.values())) > 0
    assert sum(list(hospital_admissions.values())) == hospital_admissions_logged.sum()
    pd._testing.assert_series_equal(
        hospital_admissions_df,
        hospital_admissions_logged,
        check_names=False,
        check_dtype=False,
    )


def test__read_infected_and_dead():
    world = make_dummy_world(infected=False)
    output_path = "dummy_results"
    logger = Logger(save_path=output_path)
    timer = Timer(initial_day="2020-03-10", total_days=15)
    ids_dead, ids_infected = [], []
    infections, deaths = defaultdict(int), defaultdict(int)
    logger.log_population(world.people)
    while timer.date <= timer.final_date and world.people.susceptible:
        time = timer.date
        ids = []
        symptoms = []
        select_random_susceptible = random.choice(
            [person for person in world.people.susceptible]
        )
        infect_dead_person(select_random_susceptible)
        for person in world.people.infected:
            new_status = person.infection.update_health_status(
                timer.now, timer.duration
            )
            ids.append(person.id)
            symptoms.append(person.infection.tag.value)
            if person.id not in ids_infected:
                ids_infected.append(person.id)
                infections[time.strftime("%Y-%m-%dT%H:%M:%S.%f")] += 1
            if (
                person.infection.symptoms.tag
                in (SymptomTag.dead_home, SymptomTag.dead_hospital, SymptomTag.dead_icu)
                and person.id not in ids_dead
            ):
                ids_dead.append(person.id)
                deaths[time.strftime("%Y-%m-%dT%H:%M:%S.%f")] += 1

            if new_status == "recovered":
                person.infection = None
            elif new_status == "dead":
                person.infection = None
                person.dead = True
        n_secondary_infections = [0] * len(ids)
        super_area_infections = {
            "holi": {
                "ids": ids,
                "symptoms": symptoms,
                "n_secondary_infections": n_secondary_infections,
            }
        }
        logger.log_infected(timer.date, super_area_infections)
        logger.log_infection_location(time)
        next(timer)
    read = ReadLogger(output_path=output_path)
    world_df = read.world_summary()
    infections_df = pd.Series(infections)
    infections_df.index = pd.to_datetime(infections_df.index)
    infections_logged = world_df["daily_infections"]
    infections_logged = infections_logged[infections_logged.values > 0]
    assert sum(list(infections.values())) == infections_logged.sum()
    pd._testing.assert_series_equal(
        infections_df, infections_logged, check_names=False, check_dtype=False,
    )

    deaths_df = pd.Series(deaths)
    deaths_df.index = pd.to_datetime(deaths_df.index)
    deaths_logged = world_df["daily_deaths"]
    deaths_logged = deaths_logged[deaths_logged.values > 0]
    print(deaths_df)
    print(deaths_logged)
    assert sum(list(deaths.values())) == deaths_logged.sum()
    pd._testing.assert_series_equal(
        deaths_df, deaths_logged, check_names=False, check_dtype=False,
    )


# test current number of infected
def test__read_current_infected():
    world = make_dummy_world(infected=False)
    output_path = "dummy_results"
    logger = Logger(save_path=output_path)
    timer = Timer(initial_day="2020-03-10", total_days=15)
    ids_infected = []
    infected = defaultdict(int)
    logger.log_population(world.people)
    while timer.date <= timer.final_date and world.people.susceptible:
        time = timer.date
        ids = []
        symptoms = []
        select_random_susceptible = random.choice(
            [person for person in world.people.susceptible]
        )
        infect_dead_person(select_random_susceptible)
        for person in world.people.infected:
            new_status = person.infection.update_health_status(
                timer.now, timer.duration
            )
            ids.append(person.id)
            ids_infected.append(person.id)
            symptoms.append(person.infection.tag.value)
            if new_status == "recovered":
                person.infection = None
            elif new_status == "dead":
                person.infection = None
                person.dead = True
            else:
                infected[time.strftime("%Y-%m-%dT%H:%M:%S.%f")] += 1
        n_secondary_infections = [0] * len(ids)
        super_area_infections = {
            "holi": {
                "ids": ids,
                "symptoms": symptoms,
                "n_secondary_infections": n_secondary_infections,
            }
        }
        logger.log_infected(timer.date, super_area_infections)
        logger.log_infection_location(time)
        next(timer)
    read = ReadLogger(output_path=output_path)
    world_df = read.world_summary()
    infected_df = pd.Series(infected)
    infected_df.index = pd.to_datetime(infected_df.index)
    infected_logged = world_df["current_infected"]
    infected_logged = infected_logged[infected_logged.values > 0]
    assert sum(list(infected.values())) == infected_logged.sum()
    pd._testing.assert_series_equal(
        infected_df, infected_logged, check_names=False, check_dtype=False,
    )


# Test hospitalisations by age
# Test hospitalisations by area
