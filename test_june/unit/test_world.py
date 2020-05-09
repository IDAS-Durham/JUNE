import pytest
from june.geography import Geography
from june.demography import Demography
from june.world_new import World
#
def test__one_area_world():
    geography = Geography.from_file(filter_key={"oa" : "E00088544"})
    world = World.from_geography(geography)
    assert len(world.areas) == 1
    assert len(world.super_areas) == 0
