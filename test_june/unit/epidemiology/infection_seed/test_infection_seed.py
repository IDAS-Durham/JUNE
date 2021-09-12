import pandas as pd
import pytest
import numpy as np
from collections import Counter
from june.geography import Geography, SuperArea, SuperAreas, Area, Region, Regions
from june.demography import Demography, Person, Population
from june import World
from june.epidemiology.infection_seed import InfectionSeed
from june.epidemiology.infection import Immunity
from pathlib import Path
from june.time import Timer
from june.groups import Cemeteries, Household

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent
    / "configs/defaults/transmission/TransmissionConstant.yaml"
)


@pytest.fixture(name="world", scope="module")
def create_world():
    household = Household()
    people = [
        Person.from_attributes(age=np.random.randint(0, 100), sex="f")
        for i in range(5000)
    ]
    for person in people:
        household.add(person)
    world = World()
    region1 = Region(name="London")
    region2 = Region(name="North East")
    world.people = Population(people)
    area_1 = Area(name="area_1", super_area=None, coordinates=None)
    area_1.people = people[:2500]
    area_2 = Area(name="area_2", super_area=None, coordinates=None)
    area_2.people = people[2500:]
    super_area_1 = SuperArea(
        "super_1", areas=[area_1], coordinates=(1.0, 1.0), region=region1
    )
    super_area_2 = SuperArea(
        "super_2", areas=[area_2], coordinates=(1.0, 2.0), region=region2
    )
    world.super_areas = SuperAreas([super_area_1, super_area_2])
    world.regions = Regions([region1, region2])
    world.cemeteries = Cemeteries()
    return world


def clean_world(world):
    for person in world.people:
        person.infection = None
        person.immunity = Immunity()


def test__simplest_seed(world, selector):
    clean_world(world)
    date = "2020-03-01"
    seed = InfectionSeed.from_uniform_cases(
        world=world, infection_selector=selector, cases_per_capita=0.1, date=date
    )
    seed.unleash_virus_per_day(
        date=pd.to_datetime(date), time=0.0, record=None, seed_past_infections=False
    )
    n_people = len(world.people)
    infected_people = len([person for person in world.people if person.infected])
    assert np.isclose(infected_people, 0.1 * n_people, rtol=1e-1)


def test__seed_strength(world, selector):
    clean_world(world)
    date = "2020-03-01"
    seed = InfectionSeed.from_uniform_cases(
        world=world,
        infection_selector=selector,
        cases_per_capita=0.05,
        date=date,
        seed_strength=10,
    )
    seed.unleash_virus_per_day(
        date=pd.to_datetime(date), time=0.0, record=None, seed_past_infections=False
    )
    n_people = len(world.people)
    infected_people = len([person for person in world.people if person.infected])
    assert np.isclose(infected_people, 0.5 * n_people, rtol=1e-1)


def test__infection_per_day(world, selector):
    clean_world(world)
    cases_per_region_df = pd.DataFrame(
        {
            "date": ["2020-04-20", "2020-04-21"],
            "London": [0.2, 0.1],
            "North East": [0.3, 0.4],
        }
    )
    cases_per_region_df.set_index("date", inplace=True)
    cases_per_region_df.index = pd.to_datetime(cases_per_region_df.index)
    seed = InfectionSeed.from_global_age_profile(
        world=world,
        infection_selector=selector,
        daily_cases_per_region=cases_per_region_df,
    )
    assert seed.min_date.strftime("%Y-%m-%d") == "2020-04-20"
    assert seed.max_date.strftime("%Y-%m-%d") == "2020-04-21"
    timer = Timer(
        initial_day="2020-04-20",
        total_days=7,
    )
    seed.unleash_virus_per_day(timer.date)
    n_sa1 = len(world.super_areas[0].people)
    n_sa2 = len(world.super_areas[0].people)
    next(timer)
    assert np.isclose(
        len([person for person in world.super_areas[0].people if person.infected])
        / n_sa1,
        0.2,
        rtol=1e-1,
    )
    assert np.isclose(
        len([person for person in world.super_areas[1].people if person.infected])
        / n_sa2,
        0.3,
        rtol=1e-1,
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)
    assert np.isclose(
        len([person for person in world.super_areas[0].people if person.infected])
        / n_sa1,
        0.2,
        rtol=1e-1,
    )
    assert np.isclose(
        len([person for person in world.super_areas[1].people if person.infected])
        / n_sa2,
        0.3,
        rtol=1e-1,
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)
    assert np.isclose(
        len([person for person in world.super_areas[0].people if person.infected])
        / n_sa1,
        0.2 + 0.1,
        rtol=1e-1,
    )
    assert np.isclose(
        len([person for person in world.super_areas[1].people if person.infected])
        / n_sa2,
        0.3 + 0.4,
        rtol=1e-1,
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)
    assert np.isclose(
        len([person for person in world.super_areas[0].people if person.infected])
        / n_sa1,
        0.2 + 0.1,
        rtol=1e-1,
    )
    assert np.isclose(
        len([person for person in world.super_areas[1].people if person.infected])
        / n_sa2,
        0.3 + 0.4,
        rtol=1e-1,
    )

    seed.unleash_virus_per_day(timer.date)
    next(timer)
    assert np.isclose(
        len([person for person in world.super_areas[0].people if person.infected])
        / n_sa1,
        0.2 + 0.1,
        rtol=1e-1,
    )
    assert np.isclose(
        len([person for person in world.super_areas[1].people if person.infected])
        / n_sa2,
        0.3 + 0.4,
        rtol=1e-1,
    )


def test__age_profile(world, selector):
    clean_world(world)
    cases_per_region_df = pd.DataFrame(
        {
            "date": ["2020-04-20", "2020-04-21"],
            "London": [0.2, 0.1],
            "North East": [0.3, 0.4],
        }
    )
    cases_per_region_df.set_index("date", inplace=True)
    cases_per_region_df.index = pd.to_datetime(cases_per_region_df.index)
    seed = InfectionSeed.from_global_age_profile(
        world=world,
        infection_selector=selector,
        daily_cases_per_region=cases_per_region_df,
        age_profile={"0-9": 0.0, "10-39": 1.0, "40-100": 0.0},
    )
    seed.unleash_virus_per_day(pd.to_datetime("2020-04-20"))
    # seed.unleash_virus(Population(world.people), n_cases=20, time=0)
    should_not_infected = [
        person
        for person in world.people
        if person.infected and (person.age < 10 or person.age >= 40)
    ]

    assert len(should_not_infected) == 0
    should_infected = len(
        [
            person
            for person in world.people
            if person.infected and (person.age >= 10 and person.age < 40)
        ]
    )
    target = (39 - 10) / 100 * 0.25
    assert np.isclose(should_infected / len(world.people), target, rtol=1e-1)


def test__ignore_previously_infected(world, selector):
    clean_world(world)
    for person in world.people[::2]:
        person.immunity.add_immunity([selector.infection_class.infection_id()])

    date = "2020-03-01"
    seed = InfectionSeed.from_uniform_cases(
        world=world, infection_selector=selector, cases_per_capita=0.1, date=date
    )
    seed.unleash_virus_per_day(
        date=pd.to_datetime(date), time=0.0, record=None, seed_past_infections=False
    )
    n_people = len(world.people)
    infected_people = len([person for person in world.people if person.infected])
    immune_people = len(
        [
            person
            for person in world.people
            if person.immunity.is_immune(selector.infection_class.infection_id())
        ]
    )
    assert np.isclose(infected_people, 0.1 * n_people, rtol=1e-1)
    assert np.isclose(immune_people, (0.1 + 0.5) * n_people, rtol=1e-1)


def test__seed_past_days(world, selector):
    clean_world(world)
    cases_per_region_df = pd.DataFrame(
        {
            "date": ["2019-02-01", "2020-03-31", "2020-04-01"],
            "London": [0.5, 0.1, 0.2],
            "North East": [0.3, 0.2, 0.3],
        }
    )
    cases_per_region_df.set_index("date", inplace=True)
    cases_per_region_df.index = pd.to_datetime(cases_per_region_df.index)
    seed = InfectionSeed.from_global_age_profile(
        world=world,
        infection_selector=selector,
        daily_cases_per_region=cases_per_region_df,
    )
    timer = Timer(
        initial_day="2020-04-01",
        total_days=7,
    )
    seed.unleash_virus_per_day(timer.date)
    recovered = 0
    infected_1 = 0
    infected_2 = 0
    for person in world.people:
        if person.infected:
            if person.infection.start_time == -1:
                infected_1 += 1
            elif person.infection.start_time == 0:
                infected_2 += 1
            else:
                assert False
        else:
            if person.immunity.is_immune(selector.infection_class.infection_id()):
                recovered += 1
    n_people = len(world.people)
    expected_recovered = (0.5 * 0.5 + 0.5 * 0.3) * n_people
    expected_inf1 = (0.5 * 0.1 + 0.5 * 0.2) * n_people
    expected_inf2 = (0.5 * 0.2 + 0.5 * 0.3) * n_people
    assert np.isclose(infected_1, expected_inf1, rtol=1e-1)
    assert np.isclose(infected_2, expected_inf2, rtol=1e-1)
    assert np.isclose(recovered, expected_recovered, rtol=1e-1)
