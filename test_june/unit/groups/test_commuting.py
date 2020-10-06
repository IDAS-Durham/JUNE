#import pytest
#
#from june import World
#from june.world import generate_world_from_geography
#from june.demography.geography import Geography, Area
#from june.demography import Person, Demography
#from june.distributors import WorkerDistributor
#from june.commute import CommuteGenerator
#from june.groups import (
#    CommuteCity,
#    CommuteCities,
#    CommuteCityDistributor,
#    CommuteHub,
#    CommuteHubs,
#    CommuteHubDistributor,
#    CommuteUnit,
#    CommuteUnits,
#    CommuteUnitDistributor,
#    CommuteCityUnit,
#    CommuteCityUnits,
#    CommuteCityUnitDistributor,
#)
#
#
#@pytest.fixture(name="super_area_commute", scope="module")
#def super_area_name():
#    return "E02002559"
#
#
#@pytest.fixture(name="geography_commute", scope="module")
#def create_geography(super_area_companies):
#    return Geography.from_file(filter_key={"super_area": [super_area_commute]})
#
#
#@pytest.fixture(name="person")
#def create_person():
#    return Person(sex="m", age=44)
#
#
#class TestCommuteCity:
#    @pytest.fixture(name="city")
#    def create_city(self, super_area_commute):
#        return CommuteCity(
#            city="Manchester",
#            metro_msoas=super_area_commute,
#            metro_centroid=[-2, 52.0],
#        )
#
#    def test__city_grouptype(self, city):
#        assert len(city.people) == 0
#        assert len(city.commutehubs) == 0
#        assert len(city.commute_internal) == 0
#        assert len(city.commutecityunits) == 0
#
#
#class TestCommuteHub:
#    @pytest.fixture(name="hub")
#    def create_hub(self):
#        return CommuteHub(city="Manchester", lat_lon=[-2, 52.0],)
#
#    def test__hub_grouptype(self, hub):
#        assert len(hub.commute_through) == 0
#        assert len(hub.commuteunits) == 0
#
#
#class TestCommuteUnit:
#    @pytest.fixture(name="unit")
#    def create_hub(self):
#        return CommuteUnit(city="Manchester", commutehub_id=0, is_peak=False,)
#
#    def test__unit_grouptype(self, unit):
#        assert len(unit.people) == 0
#        assert unit.max_passengers != 0
#
#
#class TestCommuteCityUnit:
#    @pytest.fixture(name="unit")
#    def create_hub(self):
#        return CommuteCityUnit(city="Manchester", is_peak=False,)
#
#    def test__unit_grouptype(self, unit):
#        assert len(unit.people) == 0
#        assert unit.max_passengers != 0
#
#
#class TestNewcastle:
#    @pytest.fixture(name="super_area_commute_nc")
#    def super_area_name_nc(self):
#        return ["E02001731", "E02001729"]
#
#    @pytest.fixture(name="geography_commute_nc")
#    def create_geography_nc(self, super_area_commute_nc):
#        geography = Geography.from_file({"super_area": super_area_commute_nc})
#        return geography
#
#    @pytest.fixture(name="world_nc")
#    def create_world_nc(self, geography_commute_nc):
#        world = generate_world_from_geography(
#            geography_commute_nc, include_commute=False, include_households=False
#        )
#        worker_distr = WorkerDistributor.for_geography(geography_commute_nc)
#        worker_distr.distribute(geography_commute_nc.areas, geography_commute_nc.super_areas, world.people)
#        commute_generator = CommuteGenerator.from_file()
#
#        for area in world.areas:
#            commute_gen = commute_generator.regional_gen_from_msoarea(area.name)
#            for person in area.people:
#                person.mode_of_transport = commute_gen.weighted_random_choice()
#
#        return world
#
#    @pytest.fixture(name="commutecities_nc")
#    def create_cities_with_people(self, world_nc):
#        commutecities = CommuteCities.for_super_areas(world_nc.super_areas)
#        commutecity_distributor = CommuteCityDistributor(
#            commutecities.members, world_nc.super_areas.members
#        )
#        commutecity_distributor.distribute_people()
#
#        return commutecities
#
#    def test__commutecities(self, commutecities_nc):
#        assert len(commutecities_nc.members) == 11
#        assert (len(commutecities_nc.members[7].people)) > 0
#
#    @pytest.fixture(name="commutehubs_nc")
#    def create_commutehubs_with_people(self, commutecities_nc):
#        commutehubs = CommuteHubs(commutecities_nc.members)
#        commutehubs.from_file()
#        commutehubs.init_hubs()
#        commutehub_distributor = CommuteHubDistributor(commutecities_nc.members)
#        commutehub_distributor.from_file()
#        commutehub_distributor.distribute_people()
#
#        return commutehubs
#
#    def test__commutehubs(self, commutecities_nc, commutehubs_nc):
#        assert len(commutecities_nc.members[7].commutehubs) == 4
#        # assert len(commutecities_nc.members[7].commute_internal) > 0
#
#    @pytest.fixture(name="commuteunits_nc")
#    def create_commute_units_with_people(self, commutecities_nc, commutehubs_nc):
#        commuteunits = CommuteUnits(commutehubs_nc.members)
#        commuteunits.init_units()
#        commuteunit_distributor = CommuteUnitDistributor(commutehubs_nc.members)
#        commuteunit_distributor.distribute_people()
#
#        return commuteunits
#
#    def test__commuteunits(self, commuteunits_nc):
#        assert len(commuteunits_nc.members[0].people) == 0
#
#    @pytest.fixture(name="commutecityunits_nc")
#    def create_commute_city_units_with_people(self, commutecities_nc, commutehubs_nc):
#        commutecityunits = CommuteCityUnits(commutecities_nc.members)
#        commutecityunits.init_units()
#        commutecityunit_distributor = CommuteCityUnitDistributor(
#            commutecities_nc.members
#        )
#        commutecityunit_distributor.distribute_people()
#
#        return commutecityunits
#
#    def test__commutecityunits(self, commutecityunits_nc):
#        assert len(commutecityunits_nc.members) > 0
#        # assert len(commutecityunits_nc.members[0].people) > 0
