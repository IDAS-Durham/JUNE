import pandas as pd
import pytest
import numpy as np
from june.demography.geography import Geography
from june.demography import Demography
from june import World
from june.seed import Seed
from june.infection import InfectionSelector
from pathlib import Path
from june.time import Timer

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
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
    selector = InfectionSelector.from_file(config_filename=constant_config)
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.fixture(name="seed")
def get_seed(geography, selector, demography):
    super_area_to_region = pd.DataFrame(
        {"super_area": SUPER_AREA_LIST, "region": REGION_LIST}
    )
    return Seed(geography.super_areas, selector, None, super_area_to_region)


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

    seed = Seed.from_file(super_areas=geography.super_areas, selector=selector)
    timer = Timer(initial_day="2020-03-01", total_days=15,)
    for time in timer:
        if time > timer.final_date:
            break
        if (time >= seed.min_date) and (time <= seed.max_date):
            seed.unleash_virus_per_region(time)

    n_infected = 0
    for super_area in geography.super_areas:
        for person in super_area.people:
            if person.infected:
                n_infected += 1
    n_cases = (
        seed.n_cases_region[seed.n_cases_region["region"] == "East of England"]
        .sum(axis=1)
        .loc[0]
    )
    np.testing.assert_allclose(n_cases, n_infected, rtol=0.05)


def test__seed_strength(selector,):
    geography = Geography.from_file(
        filter_key={"super_area": ["E02004940", "E02004935", "E02004936",]}
    )
    demography = Demography.for_geography(geography)
    for area in geography.areas:
        area.populate(demography)

    seed = Seed.from_file(
        super_areas=geography.super_areas, selector=selector, seed_strength=0.2
    )
    timer = Timer(initial_day="2020-03-01", total_days=15,)
    for time in timer:
        if time > timer.final_date:
            break
        if (time >= seed.min_date) and (time <= seed.max_date):
            seed.unleash_virus_per_region(time)

    n_infected = 0
    for super_area in geography.super_areas:
        for person in super_area.people:
            if person.infected:
                n_infected += 1
    n_cases = (
        seed.n_cases_region[seed.n_cases_region["region"] == "East of England"]
        .sum(axis=1)
        .loc[0]
    )
    np.testing.assert_allclose(0.2 * n_cases, n_infected, rtol=0.05)
