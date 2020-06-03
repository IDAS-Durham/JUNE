import os
from pathlib import Path
import numpy as np
import pytest

from june.demography.geography import Geography
from june.demography import Person
from june.groups import School, Schools

default_data_filename = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/processed/school_data/england_schools_data.csv"
)
default_areas_map_path = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "data/processed/geographical_data/oa_msoa_region.csv"
)
default_config_filename = (
    Path(os.path.abspath(__file__)).parent.parent.parent.parent
    / "configs/defaults/groups/schools.yaml"
)

default_config = {
    "age_range": (0, 19),
    "employee_per_clients": {"primary": 30, "secondary": 30},
}


@pytest.fixture(name="area_schools")
def area_name():
    return "E00088544"


class TestSchool:
    @pytest.fixture(name="school")
    def create_school(self):
        return School(
            coordinates=(1.0, 1.0),
            n_pupils_max=467,
            n_teachers_max=73,
            age_min=6,
            age_max=8,
            sector="primary_secondary",
        )

    def test__school_grouptype(self, school):
        assert school.SubgroupType.teachers == 0
        assert school.SubgroupType.students == 1

    def test__empty_school(self, school):
        assert bool(school.subgroups[school.SubgroupType.teachers].people) is False
        assert bool(school.subgroups[school.SubgroupType.students].people) is False

    def test__filling_school(self, school):
        person = Person(sex="f", age=7)
        school.add(person, School.SubgroupType.students)
        assert bool(school.subgroups[2].people) is True

class TestSchools:
    def test__creating_schools_from_file(self, area_schools):
        schools = Schools.from_file(
            area_names=[area_schools],
            data_file=default_data_filename,
            config_file=default_config_filename,
        )

    def test_creating_schools_for_areas(self, area_schools):
        schools = Schools.for_areas([area_schools])

    def test__creating_schools_for_zone(self, area_schools):
        schools = Schools.for_zone({"oa": [area_schools]})

    @pytest.fixture(name="schools", scope="module")
    def test__creating_schools_for_geography(self):
        geography = Geography.from_file(filter_key={"msoa": ["E02004935"]})
        return Schools.for_geography(geography)

    def test__school_nr_for_geography(self, schools):
        assert len(schools) == 4

    def test__school_is_closest_to_itself(self, schools):
        school = schools.members[0]
        age = int(0.5 * (school.age_min + school.age_max))
        closest_school = schools.get_closest_schools(age, school.coordinates, 1)
        closest_school = schools.members[
            schools.school_agegroup_to_global_indices.get(age)[closest_school[0]]
        ]
        assert closest_school == school


