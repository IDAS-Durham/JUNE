import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from june.geography import Geography
from june.geography import Area
from june.groups import *
from june.geography import Geography
from june.groups.school import Schools, School
from june.distributors.school_distributor import SchoolDistributor

default_data_filename = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/school_data/england_schools_data.csv"
default_areas_map_path = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/geographical_data/oa_msoa_region.csv"
default_config_filename = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "configs/defaults/distributors/school_distributor.yaml"

default_config = {
    "age_range": (0, 19),
    "employee_per_clients": {"primary": 30, "secondary": 30},
}

default_mandatory_age_range = (5, 18)

@pytest.fixture(name="geography", scope="module")
def create_geography():
    geography = Geography.from_file({"msoa" : ["E02004935"]})
    return geography

@pytest.fixture(name="schools", scope="module")
def make_and_populate_schools(geography):
    schools = Schools.for_geography(geography)
    school_distributor = SchoolDistributor(schools)
    school_distributor.distribute_kids_to_school(geography.areas)
    return schools



def test__all_kids_mandatory_school(schools, geography):
    """
    Check that all kids in mandatory school ages are assigned a school 
    """
    KIDS_LOW = default_mandatory_age_range[0]
    KIDS_UP = default_mandatory_age_range[1]
    lost_kids = 0
    for area in geography.areas.members:
        for person in area.people:
            if (person.age >= KIDS_LOW) and (
                    person.age <= KIDS_UP
            ):
                if person.school is None:
                    lost_kids += 1
    assert lost_kids == 0


def test__only_kids_school(geography, schools):
    ADULTS_LOW = 20
    schooled_adults = 0
    for area in geography.areas:
        for person in area.people:
            if person.age >= ADULTS_LOW:
                if person.school is not None:
                    schooled_adults += 1

    assert schooled_adults == 0


def test__n_pupils_counter(schools):
    for school in schools.members:
        n_pupils = np.sum([len(grouping.people) for grouping in school.subgroups])
        assert n_pupils == school.n_pupils


def test__age_range_schools(schools):
    n_outside_range = 0
    for school in schools.members:
        for person in school.people:
            if person.age < school.age_min or person.age > school.age_max:
                n_outside_range += 1
    assert n_outside_range == 0


def test__non_mandatory_dont_go_if_school_full(schools):
    non_mandatory_added = 0
    mandatory_age_range = default_mandatory_age_range
    for school in schools.members:
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
