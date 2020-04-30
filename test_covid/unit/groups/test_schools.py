from collections import Counter
from covid.groups import *
import pickle
import pytest
import numpy as np
import pandas as pd
from pathlib import Path


def test__total_number_schools_is_correct():
    data_directory = Path(__file__).parent.parent.parent.parent
    school_path = data_directory / "data/processed/school_data/england_schools_data.csv"
    config_path = data_directory / "configs/defaults/schools.yaml"
    school_df = pd.read_csv(school_path)
    schools = Schools.from_file(school_path, config_path)
    assert len(schools.members) == len(school_df)


@pytest.mark.parametrize("index", [5, 500])
def test__given_school_coordinate_finds_itself_as_closest(index):
    data_directory = Path(__file__).parent.parent.parent.parent
    school_path = data_directory / "data/processed/school_data/england_schools_data.csv"
    config_path = data_directory / "configs/defaults/schools.yaml"
    schools = Schools.from_file(school_path, config_path)

    school_df = pd.read_csv(school_path)
    age = int(0.5*(school_df.iloc[index].age_min + school_df.iloc[index].age_max))
    closest_school = schools.get_closest_schools(
        age,
        school_df[['latitude', 'longitude']].iloc[index].values, 
        1,
    )
    closest_school_idx = schools.school_agegroup_to_global_indices.get(age)[closest_school[0]]
    assert schools.members[closest_school_idx].name == schools.members[index].name


def test__all_kids_mandatory_school(world_ne):
    """
    Check that all kids in mandatory school ages are assigned a school 
    """
    KIDS_LOW = world_ne.schools.config['school_mandatory_age_range'][0]
    KIDS_UP = world_ne.schools.config['school_mandatory_age_range'][1]
    lost_kids = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].people)):
            if (world_ne.areas.members[i].people[j].age >= KIDS_LOW) and (
                world_ne.areas.members[i].people[j].age <= KIDS_UP
            ):
                if world_ne.areas.members[i].people[j].school is None:
                    lost_kids += 1
    assert lost_kids == 0

def test__only_kids_school(world_ne):
    """
    Check that all kids in ages between 5 and 17 are assigned a school 
    """
    ADULTS_LOW = 20 
    schooled_adults = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].people)):
            if world_ne.areas.members[i].people[j].age >= ADULTS_LOW:
                if world_ne.areas.members[i].people[j].school is not None:
                    schooled_adults += 1

    assert schooled_adults == 0

def test__n_pupils_counter(world_ne):
    for school in world_ne.schools.members:
        n_pupils = len(school.people)
        assert n_pupils == school.n_pupils

def test__non_mandatory_dont_go_if_school_full(world_ne):

    non_mandatory_added = 0
    for school in world_ne.schools.members:
        if school.n_pupils > school.n_pupils_max:
            ages = np.array([person.age for person in school.people[int(school.n_pupils_max):]])
            older_kids_when_full = np.sum(ages > world_ne.schools.config['school_mandatory_age_range'][1])
            younger_kids_when_full = np.sum(ages < world_ne.schools.config['school_mandatory_age_range'][0])
            if older_kids_when_full >0 or younger_kids_when_full>0:
                non_mandatory_added += 1

    assert non_mandatory_added == 0




