import pytest
import numpy as np

from june.demography import Person
from june.epidemiology.infection import (
    B117,
    Covid19,
    InfectionSelector,
    InfectionSelectors,
)
from june.epidemiology.epidemiology import Epidemiology
from june.event import Mutation


class MockRegion:
    def __init__(self, name):
        self.name = name


class MockArea:
    def __init__(self, super_area):
        self.super_area = super_area


class MockSuperArea:
    def __init__(self, region):
        self.region = region


class MockSimulator:
    def __init__(self, epidemiology):
        self.epidemiology = epidemiology


class MockWorld:
    def __init__(self, people):
        self.people = people


@pytest.fixture(name="c19_selector")
def covid19_selector(health_index_generator):
    return InfectionSelector(
        health_index_generator=health_index_generator,
        infection_class=Covid19,
    )


@pytest.fixture(name="c20_selector")
def covid20_selector(health_index_generator):
    return InfectionSelector(
        infection_class=B117,
        health_index_generator=health_index_generator,
    )


class TestMutations:
    @pytest.fixture(name="people")
    def create_pop(self, c19_selector):
        people = []
        london = MockRegion("London")
        london_sa = MockSuperArea(region=london)
        ne = MockRegion("North East")
        ne_sa = MockSuperArea(region=ne)
        for i in range(0, 1000):
            person = Person.from_attributes()
            if i % 2 == 0:
                person.area = MockArea(super_area=london_sa)
            else:
                person.area = MockArea(super_area=ne_sa)
            people.append(person)
        for person in people:
            c19_selector.infect_person_at_time(person, 0)
        return people

    def test_mutation(self, people, c19_selector, c20_selector):
        infection_selectors = InfectionSelectors([c19_selector, c20_selector])
        epidemiology = Epidemiology(infection_selectors=infection_selectors)
        simulator = MockSimulator(epidemiology)
        world = MockWorld(people=people)
        mutation = Mutation(
            start_time="2020-11-01",
            end_time="2020-11-02",
            mutation_id=B117.infection_id(),
            regional_probabilities={"London": 0.5, "North East": 0.01},
        )
        mutation.initialise()
        mutation.apply(world=world, simulator=simulator)
        c19_london = 0
        c19_ne = 0
        c20_london = 0
        c20_ne = 0
        for person in world.people:
            if person.infection.infection_id() == Covid19.infection_id():
                assert person.infection.__class__.__name__ == "Covid19"
                if person.region.name == "London":
                    c19_london += 1
                else:
                    assert person.region.name == "North East"
                    c19_ne += 1
            else:
                assert person.infection.infection_id() == B117.infection_id()
                assert person.infection.__class__.__name__ == "B117"
                if person.region.name == "London":
                    c20_london += 1
                else:
                    assert person.region.name == "North East"
                    c20_ne += 1
        assert np.isclose(c20_london / (c20_london + c19_london), 0.5, rtol=1e-1)
        assert np.isclose(c20_ne / (c20_ne + c19_ne), 0.01, atol=0.01)
