import numpy as np
from june.geography import Geography, GeographicalUnit
from june.demography import Demography
from june import World
from june.groups import Group, Companies, Schools, CareHomes, Hospitals, Cemeteries
import pytest
from copy import deepcopy


@pytest.fixture(name="geography", scope="module")
def make_geography():
    geography = Geography.from_file({"msoa": ["E02002512", "E02001697"]})
    return geography


@pytest.fixture(name="original_world", scope="module")
def create_world(geography):
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.carehomes = CareHomes.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.companies = Companies.for_geography(geography)
    world = World(geography, demography, include_households=True)
    return world

def sort_by_list(array, sortidx):
    return [array[i] for i in np.argsort(sortidx)]


@pytest.fixture(scope="module", name="world_after_pickle")
def original_world_after_pickle(original_world):
    w = deepcopy(original_world)
    w.to_pickle("test.pkl")
    return w


@pytest.fixture(scope="module", name="pickled_world")
def pickled_world(original_world):
    return World.from_pickle("test.pkl")


def test__check_worlds_people_match(original_world, world_after_pickle, pickled_world):
    check_worlds_people_match(original_world, world_after_pickle)
    check_worlds_people_match(original_world, pickled_world)

def check_worlds_people_match(world1, world2):
    """
    Checks all the people in world and the reconstructed pickle world,
    and checks they have they belong to the same groups.
    """
    world_people_ids = [person.id for person in world1.people.members]
    world_people = sort_by_list(list(world1.people.people), world_people_ids)

    pickled_world_people_ids = [person.id for person in world2.people.members]
    pickled_world_people = sort_by_list(
        world2.people.people, pickled_world_people_ids
    )
    for person1, person2 in zip(world_people, pickled_world_people):
        for slot in person1.__slots__:
            value = getattr(person1, slot)
            if value is None:
                assert getattr(person2, slot) is None
            else:
                if isinstance(value, Group) or isinstance(value, GeographicalUnit):
                    assert value.id == getattr(person2, slot).id
                    assert value.__class__ == getattr(person2, slot).__class__

def test__group_reconstruction(original_world, world_after_pickle, pickled_world):
    group_reconstruction(original_world, world_after_pickle)
    group_reconstruction(original_world, pickled_world)

def group_reconstruction(world1, world2):
    """
    Tests that the reconstructed groups contain the same amount of people
    """
    supergroups_names = [
        "cemeteries",
        "hospitals",
        "schools",
        "companies",
        "carehomes",
        "households",
    ]
    # supergroups_names = ["schools", "companies", "carehomes", "households"]
    for supergroup_name in supergroups_names:
        supergroup = getattr(world1, supergroup_name)
        supergroup_pickle = getattr(world2, supergroup_name)
        group_ids = [group.id for group in supergroup]
        group_ids_pickled = [group.id for group in supergroup_pickle]
        groups = sort_by_list(supergroup.members, group_ids)
        groups_pickled = sort_by_list(supergroup_pickle.members, group_ids_pickled)
        for group, group_pickled in zip(groups, groups_pickled):
            assert group.id == group_pickled.id
            for subtype in group.GroupType:
                subgroup = group[subtype]
                subgroup_pickle = group[subtype]
                assert len(subgroup) == len(subgroup_pickle)
                if len(subgroup) == 0:
                    continue
                people_list = list(subgroup._people)
                people_pickled_list = list(subgroup_pickle._people)
                people_ids = [person.id for person in people_list]
                pickle_people_ids = [person.id for person in people_pickled_list]
                people = sort_by_list(people_list, people_ids)
                people_pickle = sort_by_list(people_pickled_list, pickle_people_ids)
                for person, person_pickle in zip(people, people_pickle):
                    assert person.id == person_pickle.id

def test__areas_reconstruction(original_world, world_after_pickle, pickled_world):
    areas_reconstruction(original_world, world_after_pickle)
    areas_reconstruction(original_world, pickled_world)


def areas_reconstruction(world1, world2):
    """
    Tests that the reconstructed groups contain the same amount of people
    """
    area_ids = [area.id for area in world1.areas.members]
    pickled_area_ids = [area.id for area in world2.areas.members]
    areas = sort_by_list(world1.areas.members, area_ids)
    pickled_areas = sort_by_list(world2.areas.members, pickled_area_ids)
    assert len(areas) == len(pickled_areas)
    if len(areas) != 0:
        for area, area_pickled in zip(areas, pickled_areas):
            assert area.id == area_pickled.id
            people_ids = [person.id for person in area.people]
            pickled_people_ids = [person.id for person in area_pickled.people]
            people = sort_by_list(list(area.people), people_ids)
            people_pickled = sort_by_list(list(area_pickled.people), pickled_people_ids)
            for person, person_pickled in zip(people, people_pickled):
                assert person.id == person_pickled.id
