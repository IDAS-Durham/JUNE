from collections import Counter
from covid.groups import *
import pickle
import pytest
import numpy as np
import pandas as pd
from pathlib import Path


'''
def test__number_schools():
    data_directory = Path(__file__).parent.parent.parent.parent
    school_path = data_directory / "data/census_data/school_data/uk_schools_data.csv"
    school_df = pd.read_csv(school_path)
    schools = Schools.from_file(school_path)

    assert len(schools.members) == len(school_df)
'''

def test__given_school_coordinate_finds_itself():
    data_directory = Path(__file__).parent.parent.parent.parent
    school_path = "../data/census_data/school_data/uk_schools_data.csv"
    schools = Schools.from_file(school_path)

    school_df = pd.read_csv(school_path)
    closest_school = schools.get_closest_schools(
        3,
        np.array([school_df.iloc[0].latitude, 
            school_df.iloc[0].longitude]),
        0,
    )

    assert schools.members[closest_school[0]] == schools.members[0]

'''
def test_year_ranges_fullfilled():
    

def test_all_kids_school(world_ne):
    """
    Check that all kids in ages between 5 and 17 are assigned a school 
    """
    KIDS_LOW = 5
    KIDS_UP = 17
    lost_kids = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].people)):
            if (world_ne.areas.members[i].people[j].age >= KIDS_LOW) and (
                world_ne.areas.members[i].people[j].age <= KIDS_UP
            ):
                if world_ne.areas.members[i].people[j].school is None:
                    lost_kids += 1

    assert lost_kids == 0

def test_only_kids_school(world_ne):
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
'''

if __name__ == '__main__':
    test__given_school_coordinate_finds_itself()
