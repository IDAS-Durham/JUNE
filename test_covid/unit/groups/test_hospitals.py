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
    assert len(hospitals.members) == len(hospital_df)


@pytest.mark.parametrize("index", [5, 500])
def test__given_hospital_finds_itself_as_closest(index):
    data_directory = Path(__file__).parent.parent.parent.parent
    hospital_path = data_directory / "data/processed/hospital_data/england_hospitals.csv"
    config_path = data_directory / "configs/defaults/hospitals.yaml"
    hospital_df = pd.read_csv(hospital_path)
    hospitals = Hospitals.from_file(hospital_path, config_path)

    r_max = 150.
    distances, closest_idx = hospitals.get_closest_hospitals(
        hospital_df[["Latitude", "Longitude"]].iloc[index].values, 
        r_max,
    )

    # All distances are actually smaller than r_max
    assert np.sum(distances > r_max) == 0

    closest_hospital_idx = closest_idx[0]

    assert hospitals.members[closest_hospital_idx].name == hospitals.members[index].name

