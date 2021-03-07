import numpy as np
import pytest
import datetime

from june.event import Event, Events, DomesticCare
from june.world import World
from june.groups import Household, Households
from june.geography import Area, Areas, SuperArea, SuperAreas, Region
from june.demography import Population, Person


class TestDomesticCare:
    @pytest.fixture(name="world")
    def make_world(self):
        world = World()
        region = Region()
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
                    household = Household(type="old", area=area)
                    p1 = Person.from_attributes(age=80)
                    p2 = Person.from_attributes(age=75)
                    household.add(p1)
                    people.append(p1)
                    people.append(p2)
                    household.add(p2)
                    households.append(household)
                    area.households.append(household)
                for _ in range(10):
                    household = Household(type="random", area=area)
                    p1 = Person.from_attributes(age=50)
                    p2 = Person.from_attributes(age=30)
                    household.add(p1)
                    household.add(p2)
                    people.append(p1)
                    people.append(p2)
                    area.households.append(household)
                    households.append(household)
            super_area = SuperArea(areas=_areas, region=region)
            for area in _areas:
                area.super_area = super_area
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
        probability_care = 1 - (0.7 * 0.7)
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
        assert np.isclose(n_linked / total, probability_care, rtol=0.1)

    def test__send_carers_during_leisure(self, domestic_care, world):
        # leisure only go weekdays leisure
        domestic_care.apply(world=world, activities=["leisure"], day_type="weekday")
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
        domestic_care.apply(world=world, activities=["leisure"], day_type="weekend")
        for household in world.households:
            if household.household_to_care:
                for person in household.residents:
                    assert person.leisure is None
                    assert not person.busy

    def test__carers_dont_go_outside_leisure(self, domestic_care, world):
        # leisure only go weekdays leisure
        domestic_care.apply(
            world=world, activities=["primary_activity"], day_type="weekday"
        )
        for household in world.households:
            if household.household_to_care:
                for person in household.residents:
                    assert person.leisure is None
                    assert not person.busy

    def test__residents_stay_home(self, domestic_care, world):
        domestic_care.apply(world=world, activities=["leisure"], day_type="weekday")
        active = False
        for household in world.households:
            if household.household_to_care:
                household_to_care = household.household_to_care
                for person in household_to_care.residents:
                    active = True
                    assert person in person.residence.people
                    assert person.busy
        assert active

    def test__care_beta(self, domestic_care, world):
        domestic_care.apply(world=world, activities=["leisure"], day_type="weekday")
        for household in world.households:
            if household.household_to_care:
                household_to_care = household.household_to_care
                assert household_to_care.receiving_care
                int_house = household.get_interactive_group(None)
                beta = (
                    int_house.get_processed_beta(
                        {"household": 1, "household_visits": 2, "care_visits": 3}, {}
                    )
                    == 3
                )
