import pytest

from june.geography import Geography
from june.demography import Person
from june.groups import School, Schools
from recordclass import dataobject

class Activities(dataobject):
    residence: None
    primary_activity: None
    medical_facility: None
    commute: None
    rail_travel: None
    leisure: None

    def iter(self):
        return [getattr(self, activity) for activity in self.__fields__]




@pytest.fixture(name="geo_schools", scope="module")
def area_name():
    geography = Geography.from_file(filter_key={"super_area": ["E02004935"]})
    return geography


class TestSchool:
    @pytest.fixture(name="school")
    def create_school(self):
        return School(
            coordinates=(1.0, 1.0),
            n_pupils_max=467,
            age_min=6,
            age_max=8,
        )

    def test__school_grouptype(self, school):
        assert school.SubgroupType.teachers == 0
        assert school.SubgroupType.students == 1

    def test__empty_school(self, school):
        assert len(school.teachers.people) == 0
        for subgroup in school.subgroups[1:]:
            assert len(subgroup.people) == 0

    def test__filling_school(self, school):
        person = Person(sex="f", age=7, subgroups = Activities(None, None, None, None, None, None))

        school.add(person)
        assert bool(school.subgroups[2].people) is True


class TestSchools:
    def test__creating_schools_from_file(self, geo_schools):
        Schools.from_file(areas=geo_schools.areas)


    def test_creating_schools_for_areas(self, geo_schools):
        Schools.for_areas(geo_schools.areas)

    @pytest.fixture(name="schools", scope="module")
    def test__creating_schools_for_geography(self, geo_schools):
        return Schools.for_geography(geo_schools)

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
