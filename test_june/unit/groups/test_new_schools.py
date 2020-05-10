import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from june.geography import Geography
from june.geography import Area
from june.groups import School, Schools
from june.demography import Person


default_data_filename = Path(os.path.abspath(__file__)).parent.parent.parent / \
    "data/processed/school_data/england_schools_data.csv"
default_areas_map_path = Path(os.path.abspath(__file__)).parent.parent.parent / \
    "data/processed/geographical_data/oa_msoa_region.csv"
default_config_filename = Path(os.path.abspath(__file__)).parent.parent.parent / \
    "configs/defaults/groups/schools.yaml"


@pytest.fixture(name="geography", scope="session")
def create_geography():
    return Geography.from_file(filter_key={"msoa" : ["E02004935"]})

@pytest.fixture(name="school", scope="session")
def create_school():
    return School(
        coordinates=(1., 1.),
        n_pupils_max=467,
        n_teachers_max=73,
        age_min=6,
        age_max=19,
        sector="primary_secondary",
    )

class TestSchool:
    def test__school_grouptype(self, school):
        assert school.GroupType.teachers == 0
        assert school.GroupType.students == 1

    def test__empty_school(self, school):
        assert bool(school.subgroups[school.GroupType.teachers].people) is False
        assert bool(school.subgroups[school.GroupType.students].people) is False
    
    def test__filling_school(self, school):
        person = Person(sex="f", age=7)
        school.add(person, School.GroupType.students)
        assert bool(school.subgroups[2].people) is True

class TestSchools:
    def test__schools_for_areas(geography):
        schools = Schools.for_areas(["E00088544"])

    def test__schools_for_zone(geography):
        schools = Schools.for_zone({"oa": ["E00088544"]})

    def test__schools_for_geography(geography):
        schools = Schools.for_geography(geography)
