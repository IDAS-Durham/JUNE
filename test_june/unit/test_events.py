import numpy as np
import pytest
import datetime

from june.event import Event, Events, DomesticCare
from june.world import World
from june.groups import Household, Households
from june.geography import Area, Areas, SuperArea, SuperAreas
from june.demography import Population, Person


def test__event_dates():
    event = Event(start_time="2020-01-05", end_time="2020-12-05")
    assert event.start_time.strftime("%Y-%m-%d") == "2020-01-05"
    assert event.end_time.strftime("%Y-%m-%d") == "2020-12-05"
    assert event.is_active(datetime.datetime.strptime("2020-03-05", "%Y-%m-%d"))
    assert not event.is_active(datetime.datetime.strptime("2030-03-05", "%Y-%m-%d"))


class TestDomesticCare:
    @pytest.fixture(name="world")
    def make_world(self):
        world = World()
        super_areas = []
        areas = []
        households = []
        people = []
        for _ in range(10):
            _areas = []
            for _ in range(5):
                area = Area()
                area.households = []
                areas.append(area)
                _areas.append(area)
                for _ in range(5):
                    household = Household(type="old")
                    p1 = Person.from_attributes(age=80)
                    p2 = Person.from_attributes(age=75)
                    household.add(p1)
                    people.append(p1)
                    people.append(p2)
                    household.add(p2)
                    households.append(household)
                    area.households.append(household)
                for _ in range(10):
                    household = Household(type="random")
                    p1 = Person.from_attributes(age=50)
                    p2 = Person.from_attributes(age=30)
                    household.add(p1)
                    household.add(p2)
                    people.append(p1)
                    people.append(p2)
                    area.households.append(household)
                    households.append(household)
            super_area = SuperArea(areas=_areas)
            super_areas.append(super_area)
        world.areas = Areas(areas, ball_tree=False)
        world.super_areas = SuperAreas(super_areas, ball_tree=False)
        world.households = Households(households)
        world.people = Population(people)
        for person in world.people:
            person.busy = False
            person.subgroups.leisure = None
        for household in world.households:
            household.clear()
        return world

    @pytest.fixture(name="needs_care_probabilities")
    def make_probs(self):
        needs_care_probabilities = {"0-65": 0, "65-100": 0.3}
        return needs_care_probabilities

    @pytest.fixture(name="domestic_care")
    def make_domestic_care_event(self, needs_care_probabilities, world):
        domestic_care = DomesticCare(
            start_time="1900-01-01",
            end_time="2999-01-01",
            needs_care_probabilities=needs_care_probabilities,
        )
        domestic_care.initialise(world=world)
        return domestic_care

    def test__care_probs_read(self, domestic_care):
        assert domestic_care.needs_care_probabilities[75] == 0.3
        assert domestic_care.needs_care_probabilities[45] == 0.0

    def test__household_linking(
        self, domestic_care, world
    ):  # domestic needed for fixture
        has_at_least_one = False
        n_linked = 0
        total = 0
        for household in world.households:
            if household.type == "old":
                assert household.household_to_care is None
                total += 1
            else:
                if household.household_to_care:
                    n_linked += 1
                    assert household.household_to_care.type == "old"
                    has_at_least_one = True
        assert has_at_least_one
        assert np.isclose(n_linked / total, 0.3, rtol=0.1)

    def test__send_carers_during_leisure(self, domestic_care, world):
        # leisure only go weekdays leisure
        domestic_care.apply(world=world, activities=["leisure"], is_weekend=False)
        for household in world.households:
            if household.household_to_care:
                has_active = False
                for person in household.residents:
                    if person.leisure is not None:
                        has_active = True
                        assert person.busy
                        assert person in person.leisure
                        assert person in household.household_to_care.people
                        assert person.leisure.group.spec == "household"
                        assert person.leisure.group.type == "old"
                        break
                assert has_active

    def test__carers_dont_go_weekends(self, domestic_care, world):
        # leisure only go weekdays leisure
        domestic_care.apply(world=world, activities=["leisure"], is_weekend=True)
        for household in world.households:
            if household.household_to_care:
                for person in household.residents:
                    assert person.leisure is None
                    assert not person.busy

    def test__carers_dont_go_outside_leisure(self, domestic_care, world):
        # leisure only go weekdays leisure
        domestic_care.apply(
            world=world, activities=["primary_activity"], is_weekend=False
        )
        for household in world.households:
            if household.household_to_care:
                for person in household.residents:
                    assert person.leisure is None
                    assert not person.busy

    def test__residents_stay_home(self, domestic_care, world):
        domestic_care.apply(
            world=world, activities=["leisure"], is_weekend=False
        )
        active = False
        for household in world.households:
            if household.household_to_care:
                household_to_care = household.household_to_care
                for person in household_to_care.residents:
                    active = True
                    assert person in person.residence.people
                    assert person.busy
        assert active
