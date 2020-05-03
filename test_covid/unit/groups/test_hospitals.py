from collections import Counter
from covid.groups import *
import pickle
import pytest
import numpy as np
import pandas as pd
from pathlib import Path


def test__total_number_hospitals_is_correct():
    data_directory = Path(__file__).parent.parent.parent.parent
    hospital_path = data_directory / "data/processed/hospital_data/england_hospitals.csv"
    config_path = data_directory / "configs/defaults/hospitals.yaml"
    hospital_df = pd.read_csv(hospital_path)
    hospitals = Hospitals.from_file(hospital_path, config_path)
    assert len(schools.members) == len(school_df)


'''
@pytest.mark.parametrize("index", [5, 500])
def test__given_hospital_finds_itself_as_closest(index):
    data_directory = Path(__file__).parent.parent.parent.parent
    school_path = data_directory / "data/processed/school_data/england_schools_data.csv"
    config_path = data_directory / "configs/defaults/schools.yaml"
    schools = Schools.from_file(school_path, config_path)

    school_df = pd.read_csv(school_path)
    age = int(0.5 * (school_df.iloc[index].age_min + school_df.iloc[index].age_max))
    closest_school = schools.get_closest_schools(
        age, school_df[["latitude", "longitude"]].iloc[index].values, 1,
    )
    closest_school_idx = schools.school_agegroup_to_global_indices.get(age)[
        closest_school[0]
    ]
    assert schools.members[closest_school_idx].name == schools.members[index].name

'''
