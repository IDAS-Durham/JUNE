import pandas as pd
import pytest
import numpy as np
from collections import Counter
from june.demography.geography import Geography
from june.demography import Demography, Person
from june import World
from june.infection_seed import InfectionSeed
from june.infection import InfectionSelector
from pathlib import Path
from june.time import Timer

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/transmission/TransmissionConstant.yaml"
)


SUPER_AREA_LIST = [
    "E02004940",
    "E02004935",
    "E02004936",
    "E02004937",
    "E02004939",
    "E02005815",
]
REGION_LIST = (len(SUPER_AREA_LIST) - 1) * ["East of England"] + ["Yorkshire"]


@pytest.fixture(name="geography")
def get_geography():

    geography = Geography.from_file(filter_key={"super_area": SUPER_AREA_LIST})
    return geography


@pytest.fixture(name="demography")
def get_demography(geography):
    demography = Demography.for_geography(geography)
    for area in geography.areas:
        area.populate(demography)
    return demography


@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file(
            transmission_config_path=constant_config
            )
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.fixture(name="seed")
def get_seed(geography, selector, demography):
    super_area_to_region = pd.DataFrame(
        {"super_area": SUPER_AREA_LIST, "region": REGION_LIST}
    )
    return InfectionSeed(geography.super_areas, selector, None, super_area_to_region)

def test__filter_region(seed):
    super_areas = seed._filter_region(region="Yorkshire")

    assert len(super_areas) == 1
    assert super_areas[0].name == "E02005815"


def test__n_infected_total(seed):

    super_areas = seed._filter_region(region="East of England")
    n_cases = 100
    seed.infect_super_areas(super_areas, n_cases)

    n_infected = 0
    for super_area in super_areas:
        for person in super_area.people:
            if person.infected:
                n_infected += 1
    np.testing.assert_allclose(n_cases, n_infected, rtol=0.05)

    n_infected = 0
    for person in super_areas[1].people:
        if person.infected:
            n_infected += 1

    n_people_region = np.sum([len(super_area.people) for super_area in super_areas])
    np.testing.assert_allclose(
        n_cases / n_people_region * len(super_areas[1].people),
        n_infected,
        atol=5,
        rtol=0,
    )


def test__n_infected_total_region_seeds_only_once_per_day(selector,):
    geography = Geography.from_file(
        filter_key={"super_area": ["E02004940", "E02004935", "E02004936",]}
    )
    demography = Demography.for_geography(geography)
    for area in geography.areas:
        area.populate(demography)
    n_cases_region = pd.DataFrame(
            {'East of England': np.array([100,200, 300,400]).astype(np.int),
            'date':['2020-03-01','2020-03-02', '2020-03-03','2020-03-04',]
            }
        )
    n_cases_region.set_index('date', inplace=True)
    n_cases_region.index = pd.to_datetime(n_cases_region.index)
    seed = InfectionSeed.from_file(super_areas=geography.super_areas, 
            selector=selector,
            n_cases_region=n_cases_region)
    timer = Timer(initial_day='2020-02-29',total_days=7,)
    while timer.date <= timer.final_date:
        time = timer.date
        if (time >= seed.min_date) and (time <= seed.max_date):
            seed.unleash_virus_per_region(time)
        next(timer)
    n_infected = 0
    for super_area in geography.super_areas:
        for person in super_area.people:
            if person.infected:
                n_infected += 1
    n_cases = (
        seed.n_cases_region["East of England"]
        .sum()
    )
    np.testing.assert_allclose(n_cases, n_infected, rtol=0.05)

def test__seed_strength(selector,):
    geography = Geography.from_file(
        filter_key={"super_area": ["E02004940", "E02004935", "E02004936",]}
    )
    demography = Demography.for_geography(geography)
    for area in geography.areas:
        area.populate(demography)
    n_cases_region = pd.DataFrame(
            {'East of England': np.array([100,200, 300,400]).astype(np.int),
            'date':['2020-03-01','2020-03-02', '2020-03-03','2020-03-04',]
            }
        )
    n_cases_region.set_index('date', inplace=True)
    n_cases_region.index = pd.to_datetime(n_cases_region.index)
    seed = InfectionSeed.from_file(super_areas=geography.super_areas, 
            selector=selector,
            n_cases_region=n_cases_region,
            seed_strength=0.2)
    timer = Timer(initial_day='2020-02-29',total_days=7,)
    while timer.date <= timer.final_date:
        time = timer.date
        if (time >= seed.min_date) and (time <= seed.max_date):
            seed.unleash_virus_per_region(time)
        next(timer)
    n_infected = 0
    for super_area in geography.super_areas:
        for person in super_area.people:
            if person.infected:
                n_infected += 1
    n_cases = (
        seed.n_cases_region["East of England"]
        .sum()
    )
    np.testing.assert_allclose(0.2 * n_cases, n_infected, rtol=0.05)

def test__simple_age_profile_test(selector,):
    n_people = 10000
    ages = np.random.randint(low=0, high=100, size=n_people)
    people = [Person.from_attributes(age=ages[n]) for n in range(n_people)] 
    seed = InfectionSeed(
            super_areas=None,
            selector=selector,
            age_profile= {
                '0-9': 0.3,
                '10-39': 0.5,
                '40-100': 0.2}
            )
    choice = seed.select_from_susceptible(people, 1000, age_profile=seed.age_profile)
    ages_infected = np.array([person.age for person in people])[choice]
    count = Counter(ages_infected)
    count_0_9 = sum([count_value for count_key, count_value in count.items() if count_key < 10])
    assert count_0_9/len(ages_infected) == pytest.approx(0.3, 0.05)
    count_10_39 = sum([count_value for count_key, count_value in count.items() if count_key >= 10 and count_key < 40])
    assert count_10_39/len(ages_infected) == pytest.approx(0.5, 0.05)
    count_40_100 = sum([count_value for count_key, count_value in count.items() if count_key > 40])
    assert count_40_100/len(ages_infected) == pytest.approx(0.2, 0.05)


def test__seed_with_age_profile(selector,):
    geography = Geography.from_file(
        filter_key={"super_area": ["E02004940"]}
    )
    demography = Demography.for_geography(geography)
    for area in geography.areas:
        area.populate(demography)

    seed = InfectionSeed(
            super_areas=geography.super_areas, 
            selector=selector,
            age_profile= {
                '0-9': 0.,
                '10-39': 1.,
                '40-100': 0.}
            )

    seed.unleash_virus(100)

    should_not_infected = [person for super_area in geography.super_areas for person in super_area.people if person.infected and (person.age < 10 or person.age >=40)]

    assert len(should_not_infected) == 0

    should_infected = [person for super_area in geography.super_areas for person in super_area.people if person.infected and (person.age >= 10 and person.age < 40)]

    assert len(should_infected) == 100

