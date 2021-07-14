import pytest
import numpy as np

from june.event import IncidenceSetter
from june.world import World
from june.geography import Area, SuperArea, Areas, SuperAreas, Region, Regions
from june.demography import Person, Population

incidence_per_region = {"London": 0.1, "North East": 0.01}


class TestIncidenceSetter:
    @pytest.fixture(name="world")
    def setup(self):
        world = World()

        london_area = Area()
        london_super_area = SuperArea(areas=[london_area])
        london = Region(name="London", super_areas=[london_super_area])

        ne_area = Area()
        ne_super_area = SuperArea(areas=[ne_area])
        ne = Region(name="North East", super_areas=[ne_super_area])
        people = []

        for i in range(1000):
            person = Person.from_attributes()
            london_area.add(person)
            people.append(person)

        for i in range(1000):
            person = Person.from_attributes()
            ne_area.add(person)
            people.append(person)

        world.areas = Areas([ne_area, london_area], ball_tree=False)
        world.super_areas = SuperAreas([ne_super_area, london_super_area], ball_tree=False)
        world.regions = Regions([london, ne])
        world.people = Population(people)
        return world

    def test__removing_infections(self, world, policy_simulator):
        selector = policy_simulator.epidemiology.infection_selectors[0]
        # infect everyone
        for person in world.people:
            selector.infect_person_at_time(person, 0.0)

        setter = IncidenceSetter(
            start_time="2020-03-01",
            end_time="2020-03-02",
            incidence_per_region=incidence_per_region,
        )
        setter.apply(world, policy_simulator)
        london = world.regions.get_from_name("London")
        ne = world.regions.get_from_name("North East")

        # infected london
        infected = 0
        for person in london.people:
            if person.infected:
                infected += 1
        assert np.isclose(infected, 0.1 * len(london.people), rtol=1e-2, atol=0)

        # infected north east
        infected = 0
        for person in ne.people:
            if person.infected:
                infected += 1
        assert np.isclose(infected, 0.01 * len(ne.people), rtol=1e-2, atol=0)

    def test__adding_infections(self, world, policy_simulator):
        selector = policy_simulator.epidemiology.infection_selectors[0]
        selector.infect_person_at_time(world.regions.get_from_name("London").people[0], 0.0)
        selector.infect_person_at_time(world.regions.get_from_name("North East").people[0], 0.0)
        setter = IncidenceSetter(
            start_time="2020-03-01",
            end_time="2020-03-02",
            incidence_per_region=incidence_per_region,
        )
        setter.apply(world, policy_simulator)

        london = world.regions.get_from_name("London")
        ne = world.regions.get_from_name("North East")

        # infected london
        infected = 0
        for person in london.people:
            if person.infected:
                infected += 1
        assert np.isclose(infected, 0.1 * len(london.people), rtol=1e-2, atol=0)

        # infected north east
        infected = 0
        for person in ne.people:
            if person.infected:
                infected += 1
        assert np.isclose(infected, 0.01 * len(ne.people), rtol=1e-2, atol=0)
