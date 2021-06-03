import os
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from june.geography import Geography

from june.groups import Hospital, Hospitals
from june.demography import Person
from june.epidemiology.infection import SymptomTag, InfectionSelector, Infection
from june.paths import data_path

from pathlib import Path

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent


@pytest.fixture(name="hospitals", scope="module")
def create_hospitals():
    return Hospitals.from_file(filename=data_path / "input/hospitals/trusts.csv")


@pytest.fixture(name="hospitals_df", scope="module")
def create_hospitals_df():
    return pd.read_csv(data_path / "input/hospitals/trusts.csv")


def test__total_number_hospitals_is_correct(hospitals, hospitals_df):
    assert len(hospitals.members) == len(hospitals_df)


@pytest.mark.parametrize("index", [2, 3])
def test__given_hospital_finds_itself_as_closest(hospitals, hospitals_df, index):

    closest_idx = hospitals.get_closest_hospitals_idx(
        hospitals_df[["latitude", "longitude"]].iloc[index].values, k=10
    )

    closest_hospital_idx = closest_idx[0]
    assert hospitals.members[closest_hospital_idx] == hospitals.members[index]


@pytest.fixture(name="selector", scope="module")
def create_selector():
    selector = InfectionSelector.from_file()
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return selector


class MockArea:
    def __init__(self, coordinates):
        self.coordinates = coordinates


def test__initialize_hospitals_from_geography():
    geography = Geography.from_file({"super_area": ["E02003282", "E02005560"]})
    hospitals = Hospitals.for_geography(geography)
    assert len(hospitals.members) == 2
    assert hospitals.members[1].super_area.name == "E02005560"
    assert hospitals.members[0].super_area.name == "E02003282"
    assert hospitals.members[1].n_beds + hospitals.members[1].n_icu_beds == 468 + 41
    assert hospitals.members[0].n_beds + hospitals.members[0].n_icu_beds == 2115 + 296
    assert hospitals.members[0].trust_code == "RAJ"
