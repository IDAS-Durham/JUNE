import numpy as np
from june.geography import Geography, GeographicalUnit
from june.demography import Demography
from june import World
from june.groups import Group
from pytest import fixture


#@fixture(name="world")
# def make_world():
#    world = World.from_geography(Geography.from_file({"oa": ["E00120481"]}))
#    return world

def sort_by_list(array, sortidx):
    return [array[i] for i in np.argsort(sortidx)]

@fixture(name="pickled_world", scope="module")
def world_from_pickle(world):
    world.to_pickle("test.pkl")
    world = world.from_pickle("test.pkl")
    return world


def test__check_worlds_people_match(world, pickled_world):
    """
    Checks all the people in world and the reconstructed pickle world,
    and checks they have they belong to the same groups.
    """
    world_people_ids = [person.id for person in world.people]
    world_people = np.array(world.people.people)[np.argsort(world_people_ids)]

    pickled_world_people_ids = [person.id for person in pickled_world.people]
    pickled_world_people = np.array(pickled_world.people.people)[
        np.argsort(pickled_world_people_ids)
    ]
    for person1, person2 in zip(world_people, pickled_world_people):
        for slot in person1.__slots__:
            value = getattr(person1, slot)
            if value is None:
                assert getattr(person2, slot) is None
            else:
                if isinstance(value, Group) or isinstance(value, GeographicalUnit):
                    assert value.id == getattr(person2, slot).id
                    assert value.__class__ == getattr(person2, slot).__class__


def test__group_reconstruction(world, pickled_world):
    """
    Tests that the reconstructed groups contain the same amount of people
    """
    supergroups_names = ["hospitals", "schools", "companies", "carehomes", "households"]
    for supergroup_name in supergroups_names:
        supergroup = getattr(world, supergroup_name)
        supergroup_pickle = getattr(pickled_world, supergroup_name)
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

def test__areas_reconstruction(world, pickled_world):
    """
    Tests that the reconstructed groups contain the same amount of people
    """
    area_ids = [area.id for area in world.areas.members]
    pickled_area_ids = [area.id for area in pickled_world.areas.members]
    areas = sort_by_list(world.areas.members, area_ids)
    pickled_areas = sort_by_list(world.areas.members, pickled_area_ids)
    assert len(areas) == len(pickled_areas)
    if len(areas) != 0:
        for area, area_pickled in zip(areas, pickled_areas):
            assert area.id == area_pickled.id
            people_ids = [person.id for person in area.people]
            pickled_people_ids = [person.id for person in area_pickled.people]
            people = sort_by_list(area.people, people_ids)
            people_pickled = sort_by_list(area_pickled.people, pickled_people_ids)
            for person, person_pickled in zip(people, people_pickled):
                assert person.id == person_pickled.id


