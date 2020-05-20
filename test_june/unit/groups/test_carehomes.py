import os
import pytest
from june.demography.geography import Geography
from june.demography import Person
from june.groups.carehome import CareHome, CareHomes


class TestCareHome:
    @pytest.fixture(name="school")
    def create_carehome(self):
        return CareHome(
            n_residents = 30
            n_worker = 8,
            area = area,
        )

    def test__carehome_grouptype(self, school):
        assert school.SubgroupType.teachers == 0
        assert school.SubgroupType.students == 1

    def test__empty_carehome(self, school):
        assert bool(school.subgroups[school.SubgroupType.teachers].people) is False
        assert bool(school.subgroups[school.SubgroupType.students].people) is False

    def test__filling_carehome(self, school):
        person = Person(sex="f", age=7)
        school.add(person, School.SubgroupType.students)
        assert bool(school.subgroups[2].people) is True


class TestCareHomes:
    @pytest.fixture(name="carehomes", scope="module")
    def test__creating_carehomes_for_geography(self):
        geography = Geography.from_file(
            filter_key={"oa": ["E00081795", "E00082111"]}
        )
        return CareHomes.for_geography(geography)

    def test__carehome_nr_for_geography():
        assert len(carehomes) == 1
    
    def test__people_in_carehome():
        carehome = carehomes.members[0]
        assert carehome.n_residents == 24
        assert carehome.n_worker == 24
        

