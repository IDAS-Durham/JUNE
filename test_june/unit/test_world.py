from june.geography import Geography
from june import World
from june.world import generate_world_from_geography
from june.groups import Schools, Hospitals, Companies, Households, Cemeteries, CareHomes


def test__onearea_world(geography):
    geography = Geography.from_file(filter_key={"area": ["E00088544"]})
    world = generate_world_from_geography(geography)
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
    assert isinstance(world.care_homes, CareHomes)
    assert isinstance(world.companies, Companies)

def test__people_in_world_right_subgroups(world):
    dummy_people = world.people.members[:40]

    for dummy_person in dummy_people:
        for subgroup in dummy_person.subgroups.iter():
            if subgroup is not None:
                assert dummy_person in subgroup.people
