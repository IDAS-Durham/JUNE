import os
import pytest
from june.demography.geography import Geography, Area
from june.demography import Person
from june.groups.carehome import CareHome, CareHomes

@pytest.fixture(name="module_area", scope="module")
def create_area():
    g = Geography.from_file(
        filter_key={"oa" : ["E00081795"]},
    )
    return g.areas.members[0]

class TestCareHome:
    @pytest.fixture(name="module_carehome")
    def create_carehome(self, module_area: Area):
        return CareHome(
            n_residents = 30,
            n_worker = 8,
            area = module_area,
        )

    def test__carehome_grouptype(self, module_carehome):
        assert module_carehome.SubgroupType.workers == 0
        assert module_carehome.SubgroupType.residents == 1
        assert module_carehome.SubgroupType.visitors == 2

    def test__empty_carehome(self, module_carehome):
        assert (
            bool(
                module_carehome.subgroups[
                    module_carehome.SubgroupType.workers
                ].people
            ) is False
        )
        assert (
            bool(
                module_carehome.subgroups[
                    module_carehome.SubgroupType.residents
                ].people
            ) is False
        )
        assert (
            bool(
                module_carehome.subgroups[
                    module_carehome.SubgroupType.visitors
                ].people
            ) is False
        )

    def test__filling_carehome(self, module_carehome):
        person = Person(sex="m", age=33)
        module_carehome.add(person, CareHome.SubgroupType.workers)
        assert bool(module_carehome.subgroups[0].people) is True


class TestCareHomes:
    @pytest.fixture(name="module_carehomes", scope="module")
    def test__creating_carehomes_for_geography(self):
        geography = Geography.from_file(
            filter_key={"oa": ["E00081795", "E00082111"]}
        )
        return CareHomes.for_geography(geography)

    def test__carehome_nr_for_geography(self, module_carehomes):
        assert len(module_carehomes) == 1
    
    def test__people_in_carehome(self, module_carehomes):
        carehome = module_carehomes.members[0]
        assert carehome.n_residents == 24
        assert carehome.n_worker == 2
