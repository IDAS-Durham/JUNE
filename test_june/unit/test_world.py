import pytest
from june.geography import Geography
from june.demography import Demography
from june.world_new import World
from june.groups import Schools, Hospitals, Companies, Households

@pytest.fixture(name="geography", scope="module")
def create_geography():
    geography = Geography.from_file(filter_key={"oa" : ["E00088544"]})
    return geography

def test__onearea_world(geography):
    world = World.from_geography(geography)
    assert hasattr(world, 'households')
    assert isinstance(world.households, Households)
    assert len(world.areas) == 1
    assert len(world.super_areas) == 1
    assert world.super_areas.members[0].name == "E02003616" 
    assert len(world.areas.members[0].people) == 362
    assert len(world.households) <= 148

def test__world_with_schools(geography):
    geography.schools = Schools.for_geography(geography)
    world = World.from_geography(geography)
    assert hasattr(world, 'schools')
    assert isinstance(world.schools, Schools)

#def test__world_with_hospitals(geography):
#    geography.hospitals = Hospitals.for_geography(geography) 
#    world = World.from_geography(geography)
#    assert hasattr(world, 'hospitals')
#    assert isinstance(world.hospitals, Hospitals)
#
#def test__world_with_companies(geography):
#    geography.companies = Companies.for_geography(geography) 
#    world = World.from_geography(geography)
#    assert hasattr(world, 'companies')
#    assert isinstance(world.companies, Companies)
#
#
