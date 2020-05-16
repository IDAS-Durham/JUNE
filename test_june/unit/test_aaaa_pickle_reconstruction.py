import numpy as np
from collections import defaultdict, OrderedDict
from june.geography import Geography, GeographicalUnit
from june.demography import Demography
from june import World
from june.groups import Group, Companies, Schools, CareHomes, Hospitals, Cemeteries
import pytest
from copy import deepcopy


@pytest.fixture(name="geography_pickle")
def make_geography():
    geography = Geography.from_file({"msoa": ["E02006764"]})
    #geography = Geography.from_file({"oa": ["E00000121"]})
    return geography


@pytest.fixture(name="world_pickle")
def create_world(geography_pickle):
    geography = geography_pickle
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    #geography.companies = Companies.for_geography(geography)
    #geography.care_homes = CareHomes.for_geography(geography)
    world = World(geography, demography, include_households=True)
    return world

def create_world_groups_dictionary(world_to_copy):
    supergroups_names = [
        "hospitals",
        "schools",
        #"companies",
        #"care_homes",
        "households",
    ]
    supergroup_dict = {}
    for supergroup_name in supergroups_names:
        supergroup = getattr(world_to_copy, supergroup_name)
        group_dict = {}
        for group in supergroup.members:
            people_ids = []
            for person in group.people:
                people_ids.append(person.id)
            group_dict[group.id] = sorted(people_ids)
        supergroup_dict[supergroup_name] = group_dict
    return supergroup_dict 


def save_world_areas(world_to_copy, geo = "areas"):
    area_dict = {}
    for area in getattr(world_to_copy, geo):
        people_ids = []
        for person in area.people:
            people_ids.append(person.id)
        area_dict[area.id] = sorted(people_ids)
    return area_dict


def test__world_reconstruction(world_pickle):
    world = world_pickle
    # check we saved everything correctly
    original_group = create_world_groups_dictionary(world)
    original_areas = save_world_areas(world, "areas")
    original_super_areas = save_world_areas(world, "super_areas")
    world.to_pickle("test.pkl")
    broken_group = create_world_groups_dictionary(world)
    broken_areas = save_world_areas(world, "areas")
    broken_super_areas = save_world_areas(world, "super_areas")
    world = World.from_pickle("test.pkl")
    recovered_group = create_world_groups_dictionary(world)
    recovered_areas = save_world_areas(world, "areas")
    recovered_super_areas = save_world_areas(world, "super_areas")

    #assert original_group == broken_group
    assert original_group == recovered_group
    
    #assert original_areas == broken_areas
    assert original_areas == recovered_areas 

    #assert original_super_areas == broken_super_areas
    assert original_super_areas == recovered_super_areas 

