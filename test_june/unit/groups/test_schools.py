from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from june.groups import *


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
    #schools = Schools.from_file(school_path, config_path)
    school_df = pd.read_csv(school_path)
    school_df = school_df.iloc[:1000]
    schools = Schools.from_df(school_df)
    age = int(0.5 * (school_df.iloc[index].age_min + school_df.iloc[index].age_max))
    closest_school = schools.get_closest_schools(
        age, school_df[["latitude", "longitude"]].iloc[index].values, 1,
    )
    closest_school_idx = schools.school_agegroup_to_global_indices.get(age)[
        closest_school[0]
    ]
    assert schools.members[closest_school_idx].name == schools.members[index].name


def test__all_kids_mandatory_school(world_ne):
    """
    Check that all kids in mandatory school ages are assigned a school 
    """
    KIDS_LOW = world_ne.schools.mandatory_age_range[0]
    KIDS_UP = world_ne.schools.mandatory_age_range[1]
    lost_kids = 0
    for area in world_ne.areas.members:
        for person in area.subgroups[0]._people:
            if (person.age >= KIDS_LOW) and (
                    person.age <= KIDS_UP
            ):
                if person.school is None:
                    lost_kids += 1
    assert lost_kids == 0


def test__only_kids_school(world_ne):
    ADULTS_LOW = 20
    schooled_adults = 0
    for area in world_ne.areas.members:
        for person in area.subgroups[0]._people:
            if person.age >= ADULTS_LOW:
                if person.school is not None:
                    schooled_adults += 1

    assert schooled_adults == 0


def test__n_pupils_counter(world_ne):
    for school in world_ne.schools.members:
        n_pupils = np.sum([len(grouping.people) for grouping in school.subgroups])
        assert n_pupils == school.n_pupils


def test__age_range_schools(world_ne):
    n_outside_range = 0
    for school in world_ne.schools.members:
        for person in school.people:
            if person.age < school.age_min or person.age > school.age_max:
                n_outside_range += 1
    assert n_outside_range == 0


def test__non_mandatory_dont_go_if_school_full(world_ne):
    non_mandatory_added = 0
    mandatory_age_range = world_ne.schools.mandatory_age_range
    for school in world_ne.schools.members:
        if school.n_pupils > school.n_pupils_max:
            ages = np.array(
                [person.age for person in list(sorted(
                    school.people,
                    key=lambda person: person.age
                ))[int(school.n_pupils_max):]]
            )
            older_kids_when_full = np.sum(
                ages > mandatory_age_range[1]
            )
            younger_kids_when_full = np.sum(
                ages < mandatory_age_range[0]
            )
            if older_kids_when_full > 0 or younger_kids_when_full > 0:
                non_mandatory_added += 1

    assert non_mandatory_added == 0
