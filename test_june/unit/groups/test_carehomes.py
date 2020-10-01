import os
import yaml
import pytest
from june import paths
from june.geography import Geography, Area
from june.demography import Person
from june.groups.care_home import CareHome, CareHomes

default_config_file = paths.configs_path / "defaults/groups/carehome.yaml"


class TestCareHome:
    @pytest.fixture(name="carehome")
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
        assert carehome.area == "asd"
        assert carehome.n_workers == 8

