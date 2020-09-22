import pytest

from june.geography import Geography
from june.groups.travel import generate_commuting_network, Travel, ModeOfTransport
from june import World
from june.demography import Person, Population


@pytest.fixture(name="geo", scope="module")
def make_sa():
    return Geography.from_file({"super_area": ["E02001731", "E02005123"]})

@pytest.fixture(name="travel_world", scope="module")
def make_commuting_network(geo):
    world = World()
    world.areas = geo.areas
    world.super_areas = geo.super_areas
    people = []
    for i in range(12):
        person = Person.from_attributes()
        person.mode_of_transport = ModeOfTransport(is_public=True, description="asd")
        person.work_super_area = world.super_areas[0]
        world.super_areas[0].workers.append(person)
        if i % 4 == 0:
            # these people commute internally
            person.area = world.super_areas[0].areas[0]
        else:
            # these people come from abroad
            person.area = world.super_areas[1].areas[0]
        people.append(person)
    world.people = Population(people)
    travel = Travel()
    travel.initialise_commute(world)
    return world, travel

class TestCommute:
    def test__generate_commuting_network(self, travel_world):
        world, travel = travel_world
        assert len(world.cities) == 1
        city = world.cities[0]
        assert city.name == "Newcastle upon Tyne"
        assert city.super_areas[0] == "E02001731"
        assert len(city.stations) == 4
        for super_area in world.super_areas:
            if super_area.name == "E02001731":
                assert super_area.city.name == "Newcastle upon Tyne"
            else:
                assert super_area.city is None

    def test__assign_commuters_to_stations(self, travel_world):
        world, travel = travel_world
        city = world.cities[0]
        n_external_commuters = 0
        for station in city.stations:
            n_external_commuters += len(station.commuter_ids)
        n_internal_commuters = len(city.commuter_ids)
        assert n_internal_commuters == 3
        assert n_external_commuters == 9
        

    def test__get_travel_subgroup(self, travel_world):
        world, travel = travel_world
        #get internal commuter
        worker = world.people[0]
        subgroup = travel.get_commute_subgroup(worker)
        assert subgroup.group.spec == "city_transport"
        # extenral
        worker = world.people[1]
        subgroup = travel.get_commute_subgroup(worker)
        assert subgroup.group.spec == "inter_city_transport"

    def test__all_commuters_get_commute(self, travel_world):
        world, travel = travel_world
        assigned_commuters = 0
        for person in world.people:
            subgroup = travel.get_commute_subgroup(person)
            if subgroup is not None:
                assigned_commuters += 1
        commuters = 0
        for city in world.cities:
            commuters += len(city.commuter_ids)
        for station in world.stations:
            commuters += len(station.commuter_ids)
        assert commuters > 0
        assert commuters == assigned_commuters



