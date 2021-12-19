import pytest
import numpy as np
import pandas as pd
from pathlib import Path

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
    def test__get_people_to_infect(self, cis, world):
        people = world.people
        cases = cis.daily_cases_per_capita_per_age_per_region.loc[
            "2021-06-26", "London"
        ]
        total_to_infect = cis.get_total_people_to_infect(
            people=people, cases_per_capita_per_age=cases
        )
        total_50 = len([person for person in world.people if person.age < 50])
        total_100 = len([person for person in world.people if person.age >= 50])
        expected = total_50 * 0.5 + total_100 * 0.2
        assert np.isclose(total_to_infect, expected)

    def test__get_household_score(self, cis):
        household = Household()
        age_distribution = pd.Series(
            index=[0, 1, 2, 3, 4], data=[0.1, 0.2, 0, 0.1, 0.3]
        )
        for i in range(3):
            person = Person.from_attributes(age=i)
            household.add(person)
        assert np.isclose(
            cis.get_household_score(
                household=household, age_distribution=age_distribution
            ),
            0.3 / np.sqrt(3),
            rtol=1e-2,
        )
        household.add(Person.from_attributes(age=4))
        assert np.isclose(
            cis.get_household_score(
                household=household, age_distribution=age_distribution
            ),
            0.6 / np.sqrt(4),
            rtol=1e-2,
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
        assert np.isclose(np.mean(n_infected_per_household), 5, rtol=0.1)
