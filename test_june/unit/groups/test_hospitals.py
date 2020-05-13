import os
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from june.demography.geography import Geography

from june.groups import *
from june.demography import Person

default_data_filename = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/hospital_data/england_hospitals.csv"
default_config_filename = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "configs/defaults/groups/hospitals.yaml"

@pytest.fixture(name="hospitals", scope="module")
def create_hospitals():
    data_directory = Path(__file__).parent.parent.parent.parent
    return Hospitals.from_file(default_data_filename, default_config_filename)

@pytest.fixture(name="hospitals_df", scope="module")
def create_hospitals_df():
    return  pd.read_csv(default_data_filename)


def test__total_number_hospitals_is_correct(hospitals, hospitals_df):
    assert len(hospitals.members) == len(hospitals_df)


@pytest.mark.parametrize("index", [5, 20])
def test__given_hospital_finds_itself_as_closest(hospitals, hospitals_df, index):

    r_max = 150.
    distances, closest_idx = hospitals.get_closest_hospitals(
        hospitals_df[["Latitude", "Longitude"]].iloc[index].values, 
        r_max,
    )

    # All distances are actually smaller than r_max
    assert np.sum(distances > r_max) == 0

    closest_hospital_idx = closest_idx[0]

    assert hospitals.members[closest_hospital_idx].name == hospitals.members[index].name

class MockHealthInformation:
    def __init__(self, tag):
        self.tag = tag

@pytest.mark.parametrize("health_info", ["hospitalised", "intensive care"])
def test__add_patient_release_patient(hospitals, health_info):
    dummy_person = Person()
    dummy_person.health_information = MockHealthInformation(health_info) 
    assert dummy_person.in_hospital is None
    hospitals.members[0].add_as_patient(dummy_person)
    if health_info == 'hospitalised':
        assert hospitals.members[0][Hospital.GroupType.patients][0] == dummy_person
    elif health_info == 'intensive care':
        assert hospitals.members[0][Hospital.GroupType.icu_patients][0] == dummy_person
    assert dummy_person.in_hospital is not None

    hospitals.members[0].release_as_patient(dummy_person)
    assert dummy_person.in_hospital is None
    assert hospitals.members[0][Hospital.GroupType.patients].size == 0
    assert hospitals.members[0][Hospital.GroupType.icu_patients].size == 0

class MockArea:
    def __init__(self, coordinates):
        self.coordinates = coordinates


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive care"])
def test__allocate_patient_release_patient(hospitals, health_info):
    dummy_person = Person()
    dummy_person.health_information = MockHealthInformation(health_info) 
    dummy_person.area = MockArea(hospitals.members[0].coordinates)
    assert dummy_person.in_hospital is None
    hospitals.allocate_patient(dummy_person)
    if health_info == 'hospitalised':
        assert hospitals.members[0][Hospital.GroupType.patients][0] == dummy_person
    elif health_info == 'intensive care':
        assert hospitals.members[0][Hospital.GroupType.icu_patients][0] == dummy_person
        #assert list(dummy_person.in_hospital.patients)[0] == dummy_person
    #elif health_info == 'intensive care':
    #    assert list(dummy_person.in_hospital.icu_patients)[0] == dummy_person
    selected_hospital = dummy_person.in_hospital
    assert dummy_person.in_hospital is not None
    dummy_person.in_hospital.release_as_patient(dummy_person)
    assert dummy_person.in_hospital is None
    assert hospitals.members[0][Hospital.GroupType.patients].size == 0
    assert hospitals.members[0][Hospital.GroupType.icu_patients].size == 0


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive care"])
def test_try_allocate_patient_to_full_hospital(hospitals, health_info):
    dummy_person = Person()
    dummy_person.health_information = MockHealthInformation(health_info) 
    dummy_person.area = MockArea(hospitals.members[0].coordinates)

    for hospital in hospitals.members:
        for _ in range(hospital.n_beds):
            hospital.add_as_patient(dummy_person)

    assert hospitals.allocate_patient(dummy_person) == None

    for hospital in hospitals.members:
        for _ in range(hospital.n_beds):
            hospital.release_as_patient(dummy_person)

def test__initialize_hospitals_from_geography():
    geography = Geography.from_file({"msoa": ["E02003999", "E02006764"]})
    hospitals = Hospitals.for_geography(geography)
    assert len(hospitals.members) == 2
    assert hospitals.members[0].n_beds + hospitals.members[0].n_icu_beds == 190
    assert hospitals.members[0].super_area.name in ["E02003999", "E02006764"]
