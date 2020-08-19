import os
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from june.demography.geography import Geography

from june.groups import Hospital, Hospitals
from june.demography import Person
from june.infection import SymptomTag
from june.infection import InfectionSelector, Infection
from june.paths import data_path 

from pathlib import Path
path_pwd = Path(__file__)
dir_pwd  = path_pwd.parent

@pytest.fixture(name="hospitals", scope="module")
def create_hospitals():
    return Hospitals.from_file(filename=data_path / 'input/hospitals/trusts.csv')


@pytest.fixture(name="hospitals_df", scope="module")
def create_hospitals_df():
    return pd.read_csv(data_path / "input/hospitals/trusts.csv")


def test__total_number_hospitals_is_correct(hospitals, hospitals_df):
    assert len(hospitals.members) == len(hospitals_df)


@pytest.mark.parametrize("index", [2, 3])
def test__given_hospital_finds_itself_as_closest(hospitals, hospitals_df, index):

    closest_idx = hospitals.get_closest_hospitals(
        hospitals_df[["latitude", "longitude"]].iloc[index].values, k=10
    )

    closest_hospital_idx = closest_idx[0]
    assert hospitals.members[closest_hospital_idx] == hospitals.members[index]


class MockHealthInformation:
    def __init__(self, tag):
        self.tag = tag

@pytest.fixture(name='selector', scope='module')
def create_selector():
    selector = InfectionSelector.from_file()
    selector.recovery_rate            = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive_care"])
def test__add_patient_release_patient(hospitals, health_info, selector):
    dummy_person = Person().from_attributes(age=80, sex='m')
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = getattr(SymptomTag, health_info)
    assert dummy_person.medical_facility is None
    hospitals.members[0].add_as_patient(dummy_person)
    if health_info == "hospitalised":
        assert hospitals.members[0][Hospital.SubgroupType.patients][0] == dummy_person
    elif health_info == "intensive_care":
        assert (
            hospitals.members[0][Hospital.SubgroupType.icu_patients][0] == dummy_person
        )
    assert dummy_person.medical_facility is not None

    hospitals.members[0].release_as_patient(dummy_person)
    assert dummy_person.medical_facility is None


class MockArea:
    def __init__(self, coordinates):
        self.coordinates = coordinates


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive_care"])
def test__allocate_patient_release_patient(hospitals, health_info, selector):
    dummy_person = Person().from_attributes(age=80, sex='m')
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.area = MockArea(hospitals.members[-1].coordinates)
    assert dummy_person.medical_facility is None
    dummy_person.health_information.infection.symptoms.tag = getattr(SymptomTag, health_info)
    hospitals.allocate_patient(dummy_person)
    if health_info == "hospitalised":
        assert (
            dummy_person in hospitals.members[-1][Hospital.SubgroupType.patients].people
        )
    elif health_info == "intensive_care":
        assert (
            dummy_person
            in hospitals.members[-1][Hospital.SubgroupType.icu_patients].people
        )
    selected_hospital = dummy_person.medical_facility
    assert dummy_person.medical_facility is not None
    dummy_person.medical_facility.group.release_as_patient(dummy_person)
    assert dummy_person.medical_facility is None


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive_care"])
def test_try_allocate_patient_to_full_hospital(hospitals, health_info, selector):
    dummy_person = Person().from_attributes(age=80, sex='m')
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = getattr(SymptomTag, health_info)

    dummy_person.area = MockArea(hospitals.members[0].coordinates)

    for hospital in hospitals.members:
        for _ in range(int(hospital.n_beds)):
            hospital.add_as_patient(dummy_person)

    hospitals.allocate_patient(dummy_person) 
    if health_info == 'hospitalised':
        assert len(dummy_person.medical_facility.people) > dummy_person.medical_facility.group.n_beds
    elif health_info == 'intensive_care':
        assert len(dummy_person.medical_facility.people) > dummy_person.medical_facility.group.n_icu_beds

    for hospital in hospitals.members:
        for _ in range(int(hospital.n_beds)):
            hospital.release_as_patient(dummy_person)


def test__initialize_hospitals_from_geography():
    geography = Geography.from_file({"super_area": ["E02003282", "E02005560"]})
    hospitals = Hospitals.for_geography(geography)
    assert len(hospitals.members) == 2
    assert hospitals.members[0].n_beds + hospitals.members[0].n_icu_beds == 468 + 41 
    assert hospitals.members[0].super_area.name == 'E02005560' 
    assert hospitals.members[1].n_beds + hospitals.members[1].n_icu_beds == 2115 + 296 
    assert hospitals.members[1].trust_code == 'RAJ' 
