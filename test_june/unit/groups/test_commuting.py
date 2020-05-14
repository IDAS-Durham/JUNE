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

class TestNewcastle:

    @pytest.fixture(name="super_area_commute_nc")
    def super_area_name_nc(self):
        return ['E02001731', 'E02001729', 'E02001688', 'E02001689', 'E02001736',
                'E02001720', 'E02001724', 'E02001730', 'E02006841', 'E02001691',
                'E02001713', 'E02001712', 'E02001694', 'E02006842', 'E02001723',
                'E02001715', 'E02001710', 'E02001692', 'E02001734', 'E02001709']
    
    @pytest.fixture(name="geography_commute_nc")
    def create_geography_nc(self, super_area_commute_nc):
        geography = Geography.from_file(
            {"msoa": super_area_commute_nc}
        )
        return geography

    #def create_demography():

    
    
