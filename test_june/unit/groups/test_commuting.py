import os
from pathlib import Path

import pytest
import numpy as np
import pandas as pd

from june.geography import Geography
from june.geography import Area
from june.demography import Person
from june.groups import CommuteCity, CommuteCities

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
            commutecity_id = 0,
            city = 'Manchester',
            metro_msoas = super_area_commute,
            metro_centroid = [-2,52.]
        )

    def test__city_grouptype(self, city):
        assert len(city.GroupType.passengers) == 0
