import pytest
from june.geography import Geography
from june.demography import Demography
from june.world_new import World

@pytest.fixture(name="onearea_world", scope="session")
def create_onearea_world():
    geography = Geography.from_file(filter_key={"oa" : ["E00088544"]})
    world = World.from_geography(geography)
    return world

def test__onearea_world(onearea_world):
    assert len(onearea_world.areas) == 1
    assert len(onearea_world.super_areas) == 1
    assert onearea_world.super_areas.members[0].name == "E02003616" 
    assert len(onearea_world.areas.members[0].people) == 362

def test__onearea_world_households(onearea_world):
    assert len(onearea_world.households) <= 148

def test__problematic_area():
    geography = Geography.from_file(filter_key={"oa" : ["E00042595"]})
    world = World.from_geography(geography)





