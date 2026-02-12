import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from june.epidemiology.infection_seed.exact_num_infection_seed import (
    ExactNumClusteredInfectionSeed,
    ExactNumInfectionSeed,
)
from june.demography import Person, Population
from june.geography import Area, SuperArea, Areas, SuperAreas, Region, Regions
from june.world import World
from june.groups import Household, Households, Cemeteries


@pytest.fixture(name="world")
def create_world():
    area_1 = Area(name="area_1", super_area=None, coordinates=None)
    area_2 = Area(name="area_2", super_area=None, coordinates=None)
    super_area_1 = SuperArea("super_1", areas=[area_1], coordinates=(1.0, 1.0))
    super_area_2 = SuperArea("Durham", areas=[area_2], coordinates=(1.0, 2.0))
    region1 = Region(name="London", super_areas=[super_area_1])
    region2 = Region(name="North East", super_areas=[super_area_2])
    super_area_1.region = region1
    super_area_2.region = region2
    area_1.super_area = super_area_1
    area_2.super_area = super_area_2

    households = []
    people = [Person.from_attributes(age=i % 100) for i in range(10000)]
    area_1.people = people[: int(len(people) / 2)]
    for i in range(1000):
        h = Household(area=area_1)
        area_1.households.append(h)
        for j in range(i * 5, 5 * (i + 1)):
            h.add(people[j])
            people[j].area = area_1
        households.append(h)
    area_2.people = people[int(len(people) / 2) :]
    for i in range(1000, 2000):
        h = Household(area=area_2)
        area_2.households.append(h)
        for j in range(i * 5, 5 * (i + 1)):
            h.add(people[j])
            people[j].area = area_2
        households.append(h)

    world = World()
    world.households = Households(households)
    world.people = Population(people)
    world.areas = Areas(areas=[area_1, area_2], ball_tree=False)
    world.super_areas = SuperAreas([super_area_1, super_area_2])
    world.regions = Regions([region1, region2])
    world.cemeteries = Cemeteries()
    return world


def test__world(world):
    assert len(world.people) == 10000
    assert len(world.households) == 2000
    for h in world.households:
        assert len(h.residents) == 5
    for person in world.people:
        assert person.residence is not None


@pytest.fixture(name="cases")
def make_cases():
    """
    Seed two days, 40 of those aged 0-50, and 15 aged 50-100 in London per day
    """
    ret = pd.read_csv(
        Path(__file__).parent / "exact_num_cases_per_region.csv", index_col=[0, 1]
    )
    return ret


@pytest.fixture(name="cis")
def create_seed(world, selector, cases):
    cis = ExactNumClusteredInfectionSeed(
        world=world,
        infection_selector=selector,
        daily_cases_per_capita_per_age_per_region=cases,
        seed_past_infections=True,
    )
    return cis


class TestExactNumInfectOneHousehold:
    def test__get_household_score(self, cis):

        household = Household()
        age_distribution = pd.Series(index=["0-50", "50-100"], data=[0.1, 0.3])
        for i in [20, 50]:
            person = Person.from_attributes(age=i)
            household.add(person)
        assert np.isclose(
            cis.get_household_score(
                household=household, age_distribution=age_distribution
            ),
            0.4 / np.sqrt(2),
            rtol=1e-2,
        )
        household.add(Person.from_attributes(age=40))
        assert np.isclose(
            cis.get_household_score(
                household=household, age_distribution=age_distribution
            ),
            0.5 / np.sqrt(3),
            rtol=1e-2,
        )

    def test__infect_super_area(self, cis, world):
        date = "2020-03-01"
        super_area = world.super_areas[1]
        time = 0
        cases_per_capita_per_age = cis.daily_cases_per_capita_per_age_per_region.loc[
            date, "Durham"
        ]
        cis.infect_super_area(
            super_area=super_area,
            time=time,
            cases_per_capita_per_age=cases_per_capita_per_age,
        )

        infected_Durham50 = len(
            [
                person
                for person in world.people
                if person.age < 50
                and person.infected
                and person.super_area.name == "Durham"
            ]
        )
        assert infected_Durham50 == cases_per_capita_per_age["0-50"]

        infected_Durham100 = len(
            [
                person
                for person in world.people
                if person.age >= 50
                and person.infected
                and person.super_area.name == "Durham"
            ]
        )
        assert infected_Durham100 == cases_per_capita_per_age["50-100"]

        infected_London50 = len(
            [
                person
                for person in world.people
                if person.age < 50
                and person.infected
                and person.region.name == "London"
            ]
        )
        assert infected_London50 == 0

        infected_London100 = len(
            [
                person
                for person in world.people
                if person.age >= 50
                and person.infected
                and person.region.name == "London"
            ]
        )
        assert infected_London100 == 0

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
