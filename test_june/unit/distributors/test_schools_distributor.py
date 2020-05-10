import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from june.geography import Geography
from june.geography import Area
from june.groups import *

default_data_filename = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/school_data/england_schools_data.csv"
default_areas_map_path = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/geographical_data/oa_msoa_region.csv"
default_config_filename = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "configs/defaults/groups/schools.yaml"

default_config = {
    "age_range": (0, 19),
    "employee_per_clients": {"primary": 30, "secondary": 30},
}


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
