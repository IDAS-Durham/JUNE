import pytest
import datetime

from june.events import Event, Events, DomesticCareEvent
from june.world import World
from june.group import Household, Households
from june.geography import Area, Areas, SuperArea, SuperAreas
from june.demography import Population, Person


def test__event_dates():
    event = Event(start_date="2020-01-05", end_date="2020-12-05")
    assert event.start_date.strftime("%Y/%m/%d") == "2020-01-05"
    assert event.end_date.strftime("%Y/%m/%d") == "2020-12-05"
    assert event.is_active(datetime.datetime.strptime("2020-03-05", "%Y/%m%d"))
    assert not event.is_active(datetime.datetime.strptime("2030-03-05", "%Y/%m%d"))


class TestDomesticCareEvent:
    @pytest.fixture(name="world")
    def make_world():
        world = World()
        super_areas = []
        areas = []
        households = []
        people = people()
        for _ in range(10):
            _areas = []
            for _ in range(5):
                area = Area()
                area.households = []
                _areas.append(area)
                for _ in range(5):
                    household = Household(type="old")
                    p1 = Person.from_attributes(age=80)
                    p2 = Person.from_attributes(age=75)
                    household.add(p1)
                    household.add(p2)
                    households.append(household)
                    area.households.append(household)
                for _ in range(10):
                    household = Household(type="random")
                    p1 = Person.from_attributes(age=50)
                    p2 = Person.from_attributes(age=30)
                    household.add(p1)
                    household.add(p2)
                    area.households.append(household)
                    households.append(household)
            super_area = SuperArea(areas=_areas)
            super_areas.append(super_area)
        world.areas = Areas(areas)
        world.super_areas = SuperAreas(super_areas)
        world.households = Households(households)
        return world

    @pytest.fixture(name="needs_care_probabilities")
    def make_probs(self):
        needs_care_probabilities = {"0-65": 0, "65-100": 0.3}
        return needs_care_probabilities

    @pytest.fixture(name="domestic_care")
    def make_domestic_care_event(self, needs_care_probabilities, world):
        domestic_care = DomesticCareEvent(
            start_date="1900-01-01",
            end_date="2999-01-01",
            needs_care_probabilities=needs_care_probabilities,
        )
        domestic_care.initialise_event(world=world)
        return domestic_care

    def test__care_probs_read(self, domestic_care):
        assert domestic_care._get_needs_probabilities(age=75) == 0.3
        assert domestic_care._get_needs_probabilities(age=45) == 0.0

    def test__household_linking(self, domestic_care, world): # domestic needed for fixture
        has_at_least_one = False
        for household in world.households:
            if household.type == "old":
                assert household.household_to_care is None 
            else:
                if household.household_to_care:
                    assert household.household_to_care.household_to_care.type == "old"
                    has_at_least_one = True
        assert has_at_least_one

    def test__send_carers(self, domestic_care, world):
        for person in world.people:
            person.busy = False
            person.subgroups.leisure = None
        for household in world.households:
            household.clear()
        domestic_care.apply(world=world)
        for household in world.households:
            if household.household_to_care:
                has_active = False
                for person in household.people:
                    if person.busy:
                        has_active = True
                        assert person.leisure.group.spec == "household"
                        assert person.leisure.group.type == "old"
                        break
                assert has_active



    #def test__
