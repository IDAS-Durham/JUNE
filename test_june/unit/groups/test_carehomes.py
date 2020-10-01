import os
import yaml
import pytest
from june import paths
from june.geography import Geography, Area
from june.demography import Person
from june.groups.carehome import CareHome, CareHomes

default_config_file = paths.configs_path / "defaults/groups/carehome.yaml"


class TestCareHome:
    def create_carehome(self):
        return CareHome(
            n_residents = 30,
            n_workers = 8,
            area = "asd",
        )

    def test__carehome_grouptype(self, carehome):
        assert carehome.SubgroupType.workers == 0
        assert carehome.SubgroupType.residents == 1
        assert carehome.SubgroupType.visitors == 2
        assert carehome.n_residents == 30
        assert carehome.n_workers == 8

class TestCareHomes:
    @pytest.fixture(name="carehomes", scope="module")
    def test__creating_carehomes_for_geography(self):
        geography = Geography.from_file(
            filter_key={"area": ["E00081795", "E00082111"]}
        )
        return CareHomes.for_geography(geography)

    def test__carehome_nr_for_geography(self, carehomes):
        assert len(carehomes) == 1
    
    def test__people_in_carehome(self, carehomes, module_config):
        carehome = carehomes.members[0]
        n_workers = int(
            carehome.n_residents / module_config["sector"]["Q"]["nr_of_clients"]
        )
        assert carehome.n_residents == 24
        assert n_workers == 2


