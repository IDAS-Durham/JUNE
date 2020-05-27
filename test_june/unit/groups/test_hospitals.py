import os
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from june.demography.geography import Geography

from june.groups import *
from june.demography import Person
from june.infection import SymptomTags
from june.infection import InfectionSelector, Infection

default_data_filename = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/processed/hospital_data/england_hospitals.csv"
)
default_config_filename = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "configs/defaults/groups/hospitals.yaml"
)

from pathlib import Path
path_pwd = Path(__file__)
dir_pwd  = path_pwd.parent
constant_config = dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"

@pytest.fixture(name="hospitals", scope="module")
def create_hospitals():
    data_directory = Path(__file__).parent.parent.parent.parent
    return Hospitals.from_file(default_data_filename, default_config_filename)


@pytest.fixture(name="hospitals_df", scope="module")
def create_hospitals_df():
    return pd.read_csv(default_data_filename)


def test__total_number_hospitals_is_correct(hospitals, hospitals_df):
    assert len(hospitals.members) == len(hospitals_df)


@pytest.mark.parametrize("index", [5, 20])
def test__given_hospital_finds_itself_as_closest(hospitals, hospitals_df, index):

    r_max = 150.0
    distances, closest_idx = hospitals.get_closest_hospitals(
        hospitals_df[["Latitude", "Longitude"]].iloc[index].values, r_max,
    )

    # All distances are actually smaller than r_max
    assert np.sum(distances > r_max) == 0

    closest_hospital_idx = closest_idx[0]

    assert hospitals.members[closest_hospital_idx].name == hospitals.members[index].name


class MockHealthInformation:
    def __init__(self, tag):
        self.tag = tag

@pytest.fixture(name='selector', scope='module')
def create_selector():
    selector = InfectionSelector.from_file(constant_config)
    selector.recovery_rate            = 0.05
    selector.transmission_probability = 0.7
    return selector


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive_care"])
def test__add_patient_release_patient(hospitals, health_info, selector):
    dummy_person = Person().from_attributes(age=80, sex='m')
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = getattr(SymptomTags, health_info)
    print('symptoms = ', dummy_person.health_information.infection.symptoms.tag)
    assert dummy_person.hospital is None
    hospitals.members[0].add_as_patient(dummy_person)
    if health_info == "hospitalised":
        assert hospitals.members[0][Hospital.SubgroupType.patients][0] == dummy_person
    elif health_info == "intensive_care":
        assert (
            hospitals.members[0][Hospital.SubgroupType.icu_patients][0] == dummy_person
        )
    assert dummy_person.hospital is not None

    hospitals.members[0].release_as_patient(dummy_person)
    assert dummy_person.hospital is None


class MockArea:
    def __init__(self, coordinates):
        self.coordinates = coordinates


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive_care"])
def test__allocate_patient_release_patient(hospitals, health_info, selector):
    dummy_person = Person().from_attributes(age=80, sex='m')
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.area = MockArea(hospitals.members[0].coordinates)
    assert dummy_person.hospital is None
    dummy_person.health_information.infection.symptoms.tag = getattr(SymptomTags, health_info)
    hospitals.allocate_patient(dummy_person)
    if health_info == "hospitalised":
        assert (
            dummy_person in hospitals.members[0][Hospital.SubgroupType.patients].people
        )
    elif health_info == "intensive_care":
        assert (
            dummy_person
            in hospitals.members[0][Hospital.SubgroupType.icu_patients].people
        )
    selected_hospital = dummy_person.hospital
    assert dummy_person.hospital is not None
    dummy_person.hospital.group.release_as_patient(dummy_person)
    assert dummy_person.hospital is None


@pytest.mark.parametrize("health_info", ["hospitalised", "intensive_care"])
def test_try_allocate_patient_to_full_hospital(hospitals, health_info, selector):
    dummy_person = Person().from_attributes(age=80, sex='m')
    selector.infect_person_at_time(dummy_person, 0.0)
    dummy_person.health_information.infection.symptoms.tag = getattr(SymptomTags, health_info)

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
