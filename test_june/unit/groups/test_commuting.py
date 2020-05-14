import os
from pathlib import Path

import pytest
import numpy as np
import pandas as pd

from june.geography import Geography
from june.geography import Area
from june.demography import Person
from june.groups import CommuteCity, CommuteCities, CommuteHub, CommuteHubs, CommuteUnit, CommuteUnits, CommuteCityUnit, CommuteCityUnits

@pytest.fixture(name="super_area_commute", scope="module")
def super_area_name():
    return "E02002559"

@pytest.fixture(name="geography_commute", scope="module")
def create_geography(super_area_companies):
    return Geography.from_file(filter_key={"msoa" : [super_area_commute]})

@pytest.fixture(name="person")
def create_person():
    return Person(sex="m", age=44)

class TestCommuteCity:
    @pytest.fixture(name="city")
    def create_city(self, super_area_commute):
        return CommuteCity(
            city = 'Manchester',
            metro_msoas = super_area_commute,
            metro_centroid = [-2,52.]
        )

    def test__city_grouptype(self, city):
        assert len(city.people) == 0
        assert len(city.commutehubs) == 0
        assert len(city.commute_internal) == 0
        assert len(city.commutecityunits) == 0

class TestCommuteHub:
    @pytest.fixture(name="hub")
    def create_hub(self):
        return CommuteHub(
            city = 'Manchester',
            lat_lon = [-2,52.],
        )

    def test__hub_grouptype(self, hub):
        assert len(hub.people) == 0
        assert len(hub.commuteunits) == 0

class TestCommuteUnit:
    @pytest.fixture(name="unit")
    def create_hub(self):
        return CommuteUnit(
            city = 'Manchester',
            commutehub_id = 0,
            is_peak = False,
        )

    def test__unit_grouptype(self, unit):
        assert len(unit.people) == 0
        assert unit.max_passengers != 0

class TestCommuteCityUnit:
    @pytest.fixture(name="unit")
    def create_hub(self):
        return CommuteCityUnit(
            city = 'Manchester',
            is_peak = False,
        )

    def test__unit_grouptype(self, unit):
        assert len(unit.people) == 0
        assert unit.max_passengers != 0
