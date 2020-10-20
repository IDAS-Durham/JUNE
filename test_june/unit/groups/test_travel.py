import pytest
import numpy as np

from june.geography import Geography
from june.groups.travel import Travel, ModeOfTransport
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
    for i in range(1200):
        person = Person.from_attributes()
        person.mode_of_transport = ModeOfTransport(is_public=True, description="asd")
        person.work_super_area = world.super_areas.members_by_name["E02001731"]
        world.super_areas[0].workers.append(person)
        if i % 4 == 0:
            # these people commute internally
            person.area = world.super_areas.members_by_name["E02001731"].areas[0]
        else:
            # these people come from abroad
            person.area = world.super_areas.members_by_name["E02005123"].areas[0]
        people.append(person)
    world.people = Population(people)
    travel = Travel()
    travel.initialise_commute(world, maximum_number_commuters_per_city_station=150)
    return world, travel


class TestCommute:
    def test__generate_commuting_network(self, travel_world):
        world, travel = travel_world
        assert len(world.cities) == 1
        city = world.cities[0]
        assert city.name == "Newcastle upon Tyne"
        assert city.super_areas[0] == "E02001731"
        assert len(city.city_stations) == 2
        assert len(city.inter_city_stations) == 4
        for super_area in world.super_areas:
            if super_area.name == "E02001731":
                assert super_area.city.name == "Newcastle upon Tyne"
            else:
                assert super_area.city is None

    def test__assign_commuters_to_stations(self, travel_world):
        world, travel = travel_world
        city = world.cities[0]
        n_external_commuters = 0
        n_internal_commuters = len(city.internal_commuter_ids)
        for station in city.inter_city_stations:
            n_external_commuters += len(station.commuter_ids)
        assert n_internal_commuters == 300
        assert n_external_commuters == 900

    def test__get_travel_subgroup(self, travel_world):
        world, travel = travel_world
        # get internal commuter
        worker = world.people[0]
        subgroup = travel.get_commute_subgroup(worker)
        assert subgroup.group.spec == "city_transport"
        # extenral
        worker = world.people[1]
        subgroup = travel.get_commute_subgroup(worker)
        assert subgroup.group.spec == "inter_city_transport"

    def test__number_of_commuters(self, travel_world):
        world, travel = travel_world
        public_transports = 0
        for person in world.people:
            if (
                person.mode_of_transport is not None
                and person.mode_of_transport.is_public
            ):
                if (
                    person.work_super_area.city is not None
                    and person.work_super_area.city.has_stations
                ):
                    public_transports += 1
        commuters = 0
        for city in world.cities:
            commuters += len(city.internal_commuter_ids)
            for station in city.inter_city_stations:
                commuters += len(station.commuter_ids)
        assert public_transports == commuters

    def test__all_commuters_get_commute(self, travel_world):
        world, travel = travel_world
        assigned_commuters = 0
        for person in world.people:
            subgroup = travel.get_commute_subgroup(person)
            if subgroup is not None:
                assigned_commuters += 1
        commuters = 0
        for city in world.cities:
            commuters += len(city.internal_commuter_ids)
            for station in city.inter_city_stations:
                commuters += len(station.commuter_ids)
        assert commuters > 0
        assert commuters == assigned_commuters

    def test__number_of_transports(self, travel_world):
        world, travel = travel_world
        newcastle = world.cities.get_by_name("Newcastle upon Tyne")
        seats_per_passenger = 2.28
        seats_per_train = 50

        n_city_transports = sum(
            [len(station.city_transports) for station in newcastle.city_stations]
        )
        assert n_city_transports > 0
        n_city_commuters = len(newcastle.internal_commuter_ids)
        assert n_city_commuters > 0
        assert (
            np.ceil(n_city_commuters * seats_per_passenger / seats_per_train)
            == n_city_transports
        )
        n_inter_city_transports = sum(
            len(station.inter_city_transports) for station in newcastle.inter_city_stations
        )
        assert n_inter_city_transports > 0
        n_inter_city_commuters = sum(
            len(station.commuter_ids) for station in newcastle.inter_city_stations
        )
        assert n_inter_city_commuters > 0
        assert (
            np.ceil(n_inter_city_commuters * seats_per_passenger / seats_per_train)
            == n_inter_city_transports
        )
