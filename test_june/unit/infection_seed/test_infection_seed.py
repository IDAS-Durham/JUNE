import pandas as pd
import pytest
import numpy as np
from collections import Counter
from june.demography.geography import Geography, SuperArea, SuperAreas, Area
from june.demography import Demography, Person, Population
from june import World
from june.infection_seed import InfectionSeed
from june.infection import InfectionSelector
from pathlib import Path
from june.time import Timer

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent
    / "configs/defaults/transmission/TransmissionConstant.yaml"
)


@pytest.fixture(name="world", scope="module")
def create_world():
    people = [
        Person.from_attributes(age=np.random.randint(0, 100), sex="f")
        for i in range(100)
    ]
    world = World()
    world.people = people
    area_1 = Area(name="area_1", super_area=None, coordinates=None)
    area_1.people = people[:20]
    area_2 = Area(name="area_2", super_area=None, coordinates=None)
    area_2.people = people[20:]
    super_area_1 = SuperArea("super_1", areas=[area_1], coordinates=(1.0, 1.0))
    super_area_2 = SuperArea("super_2", areas=[area_2], coordinates=(1.0, 2.0))
    super_areas = [super_area_1, super_area_2]
    world.super_areas = SuperAreas(super_areas)
    return world


def clean_world(world):
    for person in world.people:
        person.infection = None
        person.susceptibility = 1.0


def test__simplest_seed(world, selector):
    seed = InfectionSeed(world=world, infection_selector=selector,)
    n_cases = 10
    seed.unleash_virus(Population(world.people), n_cases=n_cases)
    infected_people = len([person for person in world.people if person.infected])
    assert infected_people == n_cases

def test__seed_strength(world, selector):
    clean_world(world)
    n_cases = 10
    seed = InfectionSeed(world=world, infection_selector=selector, seed_strength=0.2,)
    seed.unleash_virus(Population(world.people), n_cases=n_cases)
    infected_people = len([person for person in world.people if person.infected])
    np.testing.assert_allclose(0.2 * n_cases, infected_people, rtol=0.01)

def test__infection_by_super_area(world, selector):
    clean_world(world)
    seed = InfectionSeed(
        world=world, infection_selector=selector, 
    )
    n_daily_cases_by_super_area = pd.DataFrame(
            {
            'super_1': [10],
            'super_2': [20]
            }
            )

    seed.infect_super_areas(n_daily_cases_by_super_area)
    infected_super_1 = len([person for person in world.super_areas[0].people if person.infected])
    assert infected_super_1 == 10
    infected_super_2 = len([person for person in world.super_areas[1].people if person.infected])
    assert infected_super_2 == 20
 
def test__infection_by_super_area_errors(world, selector):
    clean_world(world)
    seed = InfectionSeed(
        world=world, infection_selector=selector, 
    )
    n_daily_cases_by_super_area = pd.DataFrame(
            {
            'date': ['2020-04-10'],
            'super_1': [10],
            'super_6': [20]
            }
            )
    with pytest.raises(KeyError, match=r"There is no data on cases for"):
        seed.infect_super_areas(n_daily_cases_by_super_area)

def test__infection_per_day(world, selector):
    clean_world(world)
    selector = InfectionSelector.from_file()
    cases_per_super_area_df = pd.DataFrame(
        {"date": ["2020-04-20", "2020-04-21"], 
            "super_1": [1, 2],
            "super_2": [5, 6]}
    )

    cases_per_super_area_df.set_index('date', inplace=True)
    cases_per_super_area_df.index = pd.to_datetime(cases_per_super_area_df.index)
    seed = InfectionSeed(
        world=world, infection_selector=selector, 
    )
    timer = Timer(initial_day="2020-04-20", total_days=7,)
    seed.unleash_virus_per_day(cases_per_super_area_df, timer.date)
    next(timer)
    assert (
        len([person for person in world.super_areas[0].people if person.infected]) == 1
    )
    assert (
        len([person for person in world.super_areas[1].people if person.infected]) == 5
    )

    seed.unleash_virus_per_day(cases_per_super_area_df, timer.date)
    next(timer)
    assert (
        len([person for person in world.super_areas[0].people if person.infected]) == 1
    )
    assert (
        len([person for person in world.super_areas[1].people if person.infected]) == 5
    )

    seed.unleash_virus_per_day(cases_per_super_area_df, timer.date)
    next(timer)

    assert (
        len([person for person in world.super_areas[0].people if person.infected])
        == 1 + 2
    )
    assert (
        len([person for person in world.super_areas[1].people if person.infected])
        == 5 + 6
    )

    seed.unleash_virus_per_day(cases_per_super_area_df, timer.date)
    next(timer)

    assert (
        len([person for person in world.super_areas[0].people if person.infected])
        == 1 + 2
    )
    assert (
        len([person for person in world.super_areas[1].people if person.infected])
        == 5 + 6
    )

    seed.unleash_virus_per_day(cases_per_super_area_df, timer.date)
    next(timer)

    assert (
        len([person for person in world.super_areas[0].people if person.infected])
        == 1 + 2
    )
    assert (
        len([person for person in world.super_areas[1].people if person.infected])
        == 5 + 6
    )



def test__age_profile(world, selector):
    clean_world(world)
    seed = InfectionSeed(
        world=world,
        infection_selector=selector,
        age_profile={"0-9": 0.0, "10-39": 1.0, "40-100": 0.0},
    )
    seed.unleash_virus(Population(world.people), n_cases=20)
    for person in world.people:
        if person.infected and (person.age <10 or person.age >= 40):
            print(person.id)
    should_not_infected = [
        person
        for person in world.people
        if person.infected and (person.age < 10 or person.age >= 40)
    ]

    assert len(should_not_infected) == 0
    should_infected = [
        person
        for person in world.people
        if person.infected and (person.age >= 10 and person.age < 40)
    ]
    assert len(should_infected) == 20 

