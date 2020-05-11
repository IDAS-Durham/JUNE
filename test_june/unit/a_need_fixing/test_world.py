import pytest
from june.geography import Geography
from june.demography import Demography
from june.world_new import World

def test__one_area_world():
    geography = Geography.from_file(filter_key={"oa" : ["E00088544"]})
    world = World.from_geography(geography)
    assert len(world.areas) == 1
    assert len(world.super_areas) == 1
    assert world.super_areas.members[0].name == "E02003616" 
    assert len(world.areas.members[0].people) == 362

