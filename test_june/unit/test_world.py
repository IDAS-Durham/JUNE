import pytest
from june.geography import Geography
from june.demography import Demography
from june import World
from june.groups import Schools, Hospitals, Companies, Households, Cemeteries, CareHomes


def test__onearea_world(geography):
    geography = Geography.from_file(filter_key={"oa": ["E00088544"]})
    world = World.from_geography(geography)
    assert hasattr(world, "households")
    assert isinstance(world.households, Households)
    assert len(world.areas) == 1
    assert len(world.super_areas) == 1
    assert world.super_areas.members[0].name == "E02003616"
    assert len(world.areas.members[0].people) == 362
    assert len(world.households) <= 148


def test__world_has_everything(world):
    assert isinstance(world.schools, Schools)
    assert isinstance(world.cemeteries, Cemeteries)
    assert isinstance(world.companies, Companies)
    assert isinstance(world.households, Households)
    assert isinstance(world.hospitals, Hospitals)
    assert isinstance(world.carehomes, CareHomes)
    assert isinstance(world.companies, Companies)
