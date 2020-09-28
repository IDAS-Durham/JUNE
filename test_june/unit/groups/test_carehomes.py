import os
import yaml
import pytest
from june import paths
from june.geography import Geography, Area
from june.demography import Person
from june.groups.carehome import CareHome, CareHomes

default_config_file = paths.configs_path / "defaults/groups/carehome.yaml"

@pytest.fixture(name="module_area", scope="module")
def create_area():
    g = Geography.from_file(
        filter_key={"area" : ["E00081795"]},
    )
    return g.areas.members[0]


@pytest.fixture(name="module_config", scope="module")
def read_config():
    with open(default_config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


class TestCareHome:
    @pytest.fixture(name="module_carehome")
    def create_carehome(self, module_area: Area):
        return CareHome(
            n_residents = 30,
            n_workers = 8,
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
            filter_key={"area": ["E00081795", "E00082111"]}
        )
        return CareHomes.for_geography(geography)

    def test__carehome_nr_for_geography(self, module_carehomes):
        assert len(module_carehomes) == 1
    
    def test__people_in_carehome(self, module_carehomes, module_config):
        carehome = module_carehomes.members[0]
        n_workers = int(
            carehome.n_residents / module_config["sector"]["Q"]["nr_of_clients"]
        )
        assert carehome.n_residents == 24
        assert n_workers == 2
