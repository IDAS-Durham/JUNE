#import pytest
#
#from june import World
#from june.geography import Geography, Area
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
#from june.groups import (
#    TravelCity,
#    TravelCities,
#    TravelCityDistributor,
#    TravelUnit,
#    TravelUnits,
#    TravelUnitDistributor,
#)
#from june.world import generate_world_from_geography
#
#
#class TestTravel:
#    @pytest.fixture(name="super_area_commute_nc")
#    def super_area_name_nc(self):
#        # return ['E02001731', 'E02001729', 'E02001688', 'E02001689', 'E02001736',
#        #        'E02001720', 'E02001724', 'E02001730', 'E02006841', 'E02001691',
#        #        'E02001713', 'E02001712', 'E02001694', 'E02006842', 'E02001723',
#        #        'E02001715', 'E02001710', 'E02001692', 'E02001734', 'E02001709']
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
#            geography_commute_nc, include_households=False, include_commute=False
#        )
#
#        return world
#
#    @pytest.fixture(name="commutecities_nc")
#    def create_commute_setup(self, world_nc):
#        commutecities = CommuteCities.for_super_areas(world_nc.super_areas)
#        assert len(commutecities.members) == 11
#
#        return commutecities
#
#    def test__travel_all(self, world_nc, commutecities_nc):
#        travelcities = TravelCities(commutecities_nc)
#        travelcities.init_cities()
#        assert len(travelcities.members) == 11
#
#        travelcity_distributor = TravelCityDistributor(
#            travelcities.members, world_nc.super_areas.members
#        )
#        travelcity_distributor.distribute_msoas()
#
#        travelunits = TravelUnits()
#        travelunit_distributor = TravelUnitDistributor(
#            travelcities.members, travelunits.members
#        )
#        travelunit_distributor.from_file()
#        travelunit_distributor.distribute_people_out()
#        assert len(travelunits.members) > 0
#
#        people = 0
#        for i in travelunits.members:
#            no_pass = i.no_passengers
#            people += no_pass
#
#        arrive = 0
#        for city in travelcities.members:
#            arrive += len(city.arrived)
#
#        assert people == arrive
#
#        travelunit_distributor.distribute_people_back()
#        assert len(travelunits.members) > 0
#
#        people = 0
#        for i in travelunits.members:
#            no_pass = i.no_passengers
#            people += no_pass
#
#        assert people == arrive
