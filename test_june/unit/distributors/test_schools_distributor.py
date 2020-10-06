import os
from pathlib import Path

import numpy as np
import pytest

from june.world import World, generate_world_from_geography
from june.geography import Geography
from june.groups.school import Schools
from june.distributors.school_distributor import SchoolDistributor

default_config_filename = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "configs/defaults/distributors/school_distributor.yaml"
)

default_mandatory_age_range = (5, 18)


@pytest.fixture(name="geography_school", scope="module")
def create_geography():
    geography = Geography.from_file({"super_area": ["E02004935"]})
    return geography


@pytest.fixture(name="school_world", scope="module")
def make_and_populate_schools(geography_school):
    schools = Schools.for_geography(geography_school)
    school_distributor = SchoolDistributor(schools)
    school_distributor.distribute_kids_to_school(geography_school.areas)
    geography_school.schools = Schools.for_geography(geography_school)
    world = generate_world_from_geography(geography_school, include_households=False)
    return world


def test__years_mapping(school_world):
    for school in school_world.schools:
        for subgroup in school.subgroups:
            if subgroup.subgroup_type != 0:
                for person in subgroup.people:
                    assert person.age == school.years[subgroup.subgroup_type - 1]


def test__all_kids_mandatory_school(school_world):
    """
    Check that all kids in mandatory school ages are assigned a school 
    """
    KIDS_LOW = default_mandatory_age_range[0]
    KIDS_UP = default_mandatory_age_range[1]
    lost_kids = 0
    for area in school_world.areas.members:
        for person in area.people:
            if (person.age >= KIDS_LOW) and (person.age <= KIDS_UP):
                if (
                    person.primary_activity is None
                    or person.primary_activity.group.spec != "school"
                    and person.primary_activity.subgroup_type != 0
                ):
                    lost_kids += 1
    assert lost_kids == 0


def test__only_kids_school(school_world):
    ADULTS_LOW = 20
    schooled_adults = 0
    for area in school_world.areas:
        for person in area.people:
            if person.age >= ADULTS_LOW:
                if (
                    person.primary_activity is not None
                    and person.primary_activity.group.spec == "school"
                    and person.primary_activity.subgroup_type != 0
                ):
                    schooled_adults += 1

    assert schooled_adults == 0


def test__n_pupils_counter(school_world):
    schools = school_world.schools
    for school in schools.members:
        n_pupils = np.sum(
            [
                len(grouping.people)
                for grouping in school.subgroups
                if grouping.subgroup_type != 0
            ]
        )
        assert n_pupils == school.n_pupils


def test__age_range_schools(school_world):
    schools = school_world.schools
    n_outside_range = 0
    for school in schools.members:
        for person in school.people:
            if person.primary_activity.subgroup_type != 0:
                if person.age < school.age_min or person.age > school.age_max:
                    n_outside_range += 1
    assert n_outside_range == 0


def test__non_mandatory_dont_go_if_school_full(school_world):
    non_mandatory_added = 0
    mandatory_age_range = default_mandatory_age_range
    schools = school_world.schools
    for school in schools.members:
        if school.n_pupils > school.n_pupils_max:
            ages = np.array(
                [
                    person.age
                    for person in list(
                        sorted(school.students, key=lambda person: person.age)
                    )[int(school.n_pupils_max) :]
                ]
            )
            older_kids_when_full = np.sum(ages > mandatory_age_range[1])
            younger_kids_when_full = np.sum(ages < mandatory_age_range[0])
            if older_kids_when_full > 0 or younger_kids_when_full > 0:
                non_mandatory_added += 1

    assert non_mandatory_added == 0


def test__teacher_distribution(school_world):
    for school in school_world.schools:
        students = len(school.students)
        teachers = len(school.teachers.people)
        ratio = students / teachers
        assert ratio < 40


def test__limit_classroom_sizes(school_world):
    school_distributor = SchoolDistributor(school_world.schools, max_classroom_size=3)
    school_distributor.limit_classroom_sizes()
    for school in school_world.schools:
        for subgroup in school.subgroups:
            if subgroup.subgroup_type != 0:
                assert len(subgroup.people) <= school_distributor.max_classroom_size
                for person in subgroup.people:
                    assert person.age == school.years[subgroup.subgroup_type - 1]
        n_pupils = np.sum(
            [
                len(grouping.people)
                for grouping in school.subgroups
                if grouping.subgroup_type != 0
            ]
        )
        assert n_pupils == school.n_pupils
