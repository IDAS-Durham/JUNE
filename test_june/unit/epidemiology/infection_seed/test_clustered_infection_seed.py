import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

from june.epidemiology.infection_seed.clustered_infection_seed import (
    ClusteredInfectionSeed,
)
from june.demography import Person, Population
from june.geography import Area, SuperArea, Areas, SuperAreas, Region, Regions
from june.world import World
from june.groups import Household, Households


@pytest.fixture(name="world")
def create_world():
    households = []
    area = Area()
    areas = Areas(areas=[area], ball_tree=False)
    super_area = SuperArea(areas=[area])
    super_areas = SuperAreas(super_areas=[super_area], ball_tree=False)
    region = Region(name="London", super_areas=[super_area])
    regions = Regions(regions=[region])
    # geography = Geography(areas=areas, super_areas=super_areas, regions=regions)
    world = World()
    world.areas = areas
    world.super_areas = super_areas
    world.regions = regions
    people = [Person.from_attributes(age=i % 100) for i in range(5000)]
    area.people = people
    for i in range(1000):
        h = Household(area=area)
        area.households.append(h)
        for j in range(i * 5, 5 * (i + 1)):
            h.add(people[j])
        households.append(h)
    world.households = Households(households)
    world.people = Population(people)
    return world


@pytest.fixture(name="cases")
def make_cases():
    """
    Seed one day, 50% of those aged 0-50, and 20% aged 50-100 in London
    """
    ret = pd.read_csv(Path(__file__).parent / "cases_per_region.csv", index_col=[0, 1])
    return ret


def test__world(world):
    assert len(world.people) == 5000
    assert len(world.households) == 1000
    for h in world.households:
        assert len(h.residents) == 5
    for person in world.people:
        assert person.residence is not None


@pytest.fixture(name="cis")
def create_seed(world, selector, cases):
    cis = ClusteredInfectionSeed(
        world=world,
        infection_selector=selector,
        daily_cases_per_capita_per_age_per_region=cases,
        seed_past_infections=True,
    )
    return cis


class TestInfectOneHousehold:
    def test__get_people_to_infect_by_age(self, cis, world):
        cases_per_capita_per_age = {}
        for age in range(0, 100):
            cases_per_capita_per_age[age] = 0
        cases_per_capita_per_age[10] = 0.5
        cases_per_capita_per_age[50] = 0.2
        cases_per_capita_per_age = pd.DataFrame(
            index=list(cases_per_capita_per_age.keys()),
            data=list(cases_per_capita_per_age.values()),
        )
        to_infect_by_age = cis.get_people_to_infect_in_super_area_by_age(
            super_area=world.super_areas[0],
            cases_per_capita_per_age=cases_per_capita_per_age,
        )
        assert to_infect_by_age[10] == 2.5
        assert to_infect_by_age[50] == 1
        for age in range(100):
            if age not in (10, 50):
                to_infect_by_age[age] == 0

    def test__person_can_be_infected(self, cis, world):
        to_infect_by_age = {0: 2, 1: 0}
        person = Person(age=1)
        assert (
            cis.can_person_be_infected(person=person, to_infect_by_age=to_infect_by_age)
            is False
        )
        person = Person(age=0)
        assert (
            cis.can_person_be_infected(person=person, to_infect_by_age=to_infect_by_age)
            is True
        )

    def test__infect_super_area(self, cis, world):
        date = "2021-06-26"
        super_area = world.super_areas[0]
        time = 0
        cases_per_capita_per_age = cis.daily_cases_per_capita_per_age_per_region.loc[
            date
        ]
        cis.infect_super_area(
            super_area=super_area,
            time=time,
            cases_per_capita_per_age=cases_per_capita_per_age,
        )
        infected_50 = len(
            [person for person in world.people if person.age < 50 and person.infected]
        )
        total_50 = len([person for person in world.people if person.age < 50])
        assert np.isclose(infected_50 / total_50, 0.5, rtol=0.10)

        infected_100 = len(
            [person for person in world.people if person.age >= 50 and person.infected]
        )
        total_100 = len([person for person in world.people if person.age >= 50])
        assert np.isclose(infected_100 / total_100, 0.2, rtol=0.10)

        # test household clustering
        n_infected_per_household = []
        for household in world.households:
            n = 0
            for person in household.residents:
                if person.infected:
                    n += 1
            if n > 0:
                n_infected_per_household.append(n)
        assert np.isclose(np.mean(n_infected_per_household), 3, rtol=0.1)
