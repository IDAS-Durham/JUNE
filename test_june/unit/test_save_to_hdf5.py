import numpy as np
import h5py
from collections import defaultdict
from itertools import count
from june.groups.leisure import generate_leisure_for_world, Pubs, Groceries, Cinemas
from june.demography import Demography, Person, Population
from june.geography import Geography, Area, SuperArea
from june.groups.travel import generate_commuting_network, Travel
from june.groups import (
    Households,
    Companies,
    Hospitals,
    Schools,
    CareHomes,
    Group,
    Universities,
)
from june.distributors import HouseholdDistributor
from june import World
from june.world import generate_world_from_geography
from june.hdf5_savers import (
    save_population_to_hdf5,
    save_geography_to_hdf5,
    save_schools_to_hdf5,
    save_hospitals_to_hdf5,
    save_care_homes_to_hdf5,
    save_households_to_hdf5,
    save_companies_to_hdf5,
    save_cities_to_hdf5,
    save_stations_to_hdf5,
    save_universities_to_hdf5,
    save_social_venues_to_hdf5,
    generate_world_from_hdf5,
)
from june.hdf5_savers import (
    load_geography_from_hdf5,
    load_population_from_hdf5,
    load_care_homes_from_hdf5,
    load_companies_from_hdf5,
    load_households_from_hdf5,
    load_population_from_hdf5,
    load_schools_from_hdf5,
    load_hospitals_from_hdf5,
    load_cities_from_hdf5,
    load_stations_from_hdf5,
    load_universities_from_hdf5,
    load_social_venues_from_hdf5,
)
from june import paths

from pytest import fixture


class TestSavePeople:
    def test__save_population(self, full_world):
        population = full_world.people
        assert len(population) > 0
        save_population_to_hdf5(population, "test.hdf5", chunk_size=500)
        pop_recovered = load_population_from_hdf5("test.hdf5", chunk_size=600)
        for person, person2 in zip(population, pop_recovered):
            for attribute_name in [
                "id",
                "age",
                "sex",
                "ethnicity",
                "sector",
                "sub_sector",
                "lockdown_status",
            ]:
                attribute = getattr(person, attribute_name)
                attribute2 = getattr(person2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert (
                person.mode_of_transport.description
                == person2.mode_of_transport.description
            )
            assert (
                person.mode_of_transport.is_public
                == person2.mode_of_transport.is_public
            )


class TestSaveHouses:
    def test__save_households(self, full_world):
        households = full_world.households
        assert len(households) > 0
        save_households_to_hdf5(households, "test.hdf5", chunk_size=500)
        households_recovered = load_households_from_hdf5("test.hdf5", chunk_size=600)
        for household, household2 in zip(households, households_recovered):
            for attribute_name in ["id", "max_size", "type"]:
                attribute = getattr(household, attribute_name)
                attribute2 = getattr(household2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2


class TestSaveCompanies:
    def test__save_companies(self, full_world):
        companies = full_world.companies
        assert len(companies) > 0
        save_companies_to_hdf5(companies, "test.hdf5", chunk_size=500)
        companies_recovered = load_companies_from_hdf5("test.hdf5", chunk_size=600)
        for company, company2 in zip(companies, companies_recovered):
            for attribute_name in ["id", "n_workers_max", "sector"]:
                attribute = getattr(company, attribute_name)
                attribute2 = getattr(company2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2


class TestSaveHospitals:
    def test__save_hospitals(self, full_world):
        hospitals = full_world.hospitals
        assert len(hospitals) > 0
        save_hospitals_to_hdf5(hospitals, "test.hdf5", chunk_size=500)
        hospitals_recovered = load_hospitals_from_hdf5("test.hdf5", chunk_size=600)
        for hospital, hospital2 in zip(hospitals, hospitals_recovered):
            for attribute_name in [
                "id",
                "n_beds",
                "n_icu_beds",
            ]:
                attribute = getattr(hospital, attribute_name)
                attribute2 = getattr(hospital2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert hospital.coordinates[0] == hospital2.coordinates[0]
            assert hospital.coordinates[1] == hospital2.coordinates[1]
            assert hospital.trust_code == hospital2.trust_code


class TestSaveSchools:
    def test__save_schools(self, full_world):
        schools = full_world.schools
        assert len(schools) > 0
        save_schools_to_hdf5(schools, "test.hdf5", chunk_size=500)
        schools_recovered = load_schools_from_hdf5("test.hdf5", chunk_size=600)
        for school, school2 in zip(schools, schools_recovered):
            for attribute_name in [
                "id",
                "n_pupils_max",
                "age_min",
                "age_max",
                "sector",
                "n_classrooms",
                "years",
            ]:
                attribute = getattr(school, attribute_name)
                attribute2 = getattr(school2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert school.coordinates[0] == school2.coordinates[0]
            assert school.coordinates[1] == school2.coordinates[1]


class TestSaveCarehomes:
    def test__save_carehomes(self, full_world):
        carehomes = full_world.care_homes
        assert len(carehomes) > 0
        save_care_homes_to_hdf5(carehomes, "test.hdf5", chunk_size=500)
        carehomes_recovered = load_care_homes_from_hdf5("test.hdf5", chunk_size=600)
        for carehome, carehome2 in zip(carehomes, carehomes_recovered):
            for attribute_name in ["id", "n_residents"]:
                attribute = getattr(carehome, attribute_name)
                attribute2 = getattr(carehome2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2


class TestSaveGeography:
    def test__save_geography(self, full_world):
        areas = full_world.areas
        super_areas = full_world.super_areas
        regions = full_world.regions
        assert len(areas) > 0
        assert len(super_areas) > 0
        assert len(regions) > 0
        geography = Geography(areas, super_areas, regions)
        save_geography_to_hdf5(geography, "test.hdf5")
        geography_recovered = load_geography_from_hdf5("test.hdf5")
        for area, area2 in zip(areas, geography_recovered.areas):
            for attribute_name in ["id", "name"]:
                attribute = getattr(area, attribute_name)
                attribute2 = getattr(area2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert area.coordinates[0] == area2.coordinates[0]
            assert area.coordinates[1] == area2.coordinates[1]

        for super_area, super_area2 in zip(
            super_areas, geography_recovered.super_areas
        ):
            for attribute_name in ["id", "name"]:
                attribute = getattr(super_area, attribute_name)
                attribute2 = getattr(super_area2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert super_area.coordinates[0] == super_area2.coordinates[0]
            assert super_area.coordinates[1] == super_area2.coordinates[1]
            
        for region, region2 in zip(
            regions, geography_recovered.regions
        ):
            for attribute_name in ["id", "name"]:
                attribute = getattr(region, attribute_name)
                attribute2 = getattr(region2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
        


class TestSaveTravel:
    def test__save_cities(self, full_world):
        cities = full_world.cities
        city_transports = full_world.city_transports
        assert len(cities) > 0
        save_cities_to_hdf5(cities, "test.hdf5")
        cities_recovered, city_transports_recovered = load_cities_from_hdf5("test.hdf5")
        assert len(cities) == len(cities_recovered)
        assert len(city_transports) == len(city_transports_recovered)
        for city, city_recovered in zip(cities, cities_recovered):
            assert city.name == city_recovered.name
            for sa1, sa2 in zip(city.super_areas, city_recovered.super_areas):
                assert sa1 == sa2
            assert city.coordinates[0] == city_recovered.coordinates[0]
            assert city.coordinates[1] == city_recovered.coordinates[1]
            assert len(city.city_transports) == len(city_recovered.city_transports)
            for ct1, ct2 in zip(city.city_transports, city_recovered.city_transports):
                assert ct1.id == ct2.id

    def test__save_stations(self, full_world):
        stations = full_world.stations
        inter_city_transports = full_world.inter_city_transports
        assert len(stations) > 0
        save_stations_to_hdf5(stations, "test.hdf5")
        stations_recovered, inter_city_transports_recovered = load_stations_from_hdf5(
            "test.hdf5"
        )
        assert len(stations) == len(stations_recovered)
        assert len(inter_city_transports) == len(inter_city_transports_recovered)
        for station, station_recovered in zip(stations, stations_recovered):
            assert station.id == station_recovered.id
            assert station.city == station_recovered.city
            assert len(station.inter_city_transports) == len(
                station_recovered.inter_city_transports
            )
            for ict1, ict2 in zip(
                station.inter_city_transports, station_recovered.inter_city_transports
            ):
                assert ict1.id == ict2.id


class TestSaveUniversities:
    def test__save_universities(self, full_world):
        universities = full_world.universities
        assert len(universities) > 0
        save_universities_to_hdf5(universities, "test.hdf5")
        universities_recovered = load_universities_from_hdf5("test.hdf5")
        for uni, uni2 in zip(universities, universities_recovered):
            for attribute_name in [
                "id",
                "n_students_max",
                "n_years",
            ]:
                attribute = getattr(uni, attribute_name)
                attribute2 = getattr(uni2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert uni.coordinates[0] == uni2.coordinates[0]
            assert uni.coordinates[1] == uni2.coordinates[1]


class TestSaveLeisure:
    def test__save_social_venues(self, full_world):
        save_social_venues_to_hdf5(
            social_venues_list=[
                full_world.pubs,
                full_world.groceries,
                full_world.cinemas,
            ],
            file_path="test.hdf5",
        )
        social_venues_dict = load_social_venues_from_hdf5("test.hdf5")
        for social_venues_spec, social_venues in social_venues_dict.items():
            for sv1, sv2 in zip(getattr(full_world, social_venues_spec), social_venues):
                assert sv1.coordinates[0] == sv2.coordinates[0]
                assert sv1.coordinates[1] == sv2.coordinates[1]
                assert sv1.id == sv2.id


class TestSaveWorld:
    @fixture(name="full_world_loaded", scope="module")
    def reaload_world(self, full_world):
        full_world.to_hdf5("test.hdf5")
        world2 = generate_world_from_hdf5("test.hdf5", chunk_size=500)
        return world2

    def test__save_geography(self, full_world, full_world_loaded):
        assert len(full_world.areas) == len(full_world_loaded.areas)
        for area1, area2 in zip(full_world.areas, full_world_loaded.areas):
            assert area1.id == area2.id
            assert area1.super_area.id == area2.super_area.id
            assert area1.super_area.name == area2.super_area.name
            assert area1.name == area2.name

        assert len(full_world.super_areas) == len(full_world_loaded.super_areas)
        for super_area1, super_area2 in zip(
            full_world.super_areas, full_world_loaded.super_areas
        ):
            assert super_area1.id == super_area2.id
            assert super_area1.name == super_area2.name
            assert len(super_area1.areas) == len(super_area2.areas)
            area1_ids = [area.id for area in super_area1.areas]
            area2_ids = [area.id for area in super_area2.areas]
            assert set(area1_ids) == set(area2_ids)
            sa1_areas = [super_area1.areas[idx] for idx in np.argsort(area1_ids)]
            sa2_areas = [super_area2.areas[idx] for idx in np.argsort(area2_ids)]
            for area1, area2 in zip(sa1_areas, sa2_areas):
                assert area1.id == area2.id
                assert area1.super_area.id == area2.super_area.id
                assert area1.super_area.name == area2.super_area.name
                assert area1.name == area2.name
                assert area1.super_area.region.id == area2.super_area.region.id
                assert area1.super_area.region.name == area2.super_area.region.name

        assert len(full_world.regions) == len(full_world_loaded.regions)
        for region1, region2 in zip(
            full_world.regions, full_world_loaded.regions
        ):
            assert region1.id == region2.id
            assert region1.name == region2.name
            super_area1_ids = [super_area.id for super_area in region1.super_areas]
            super_area2_ids = [super_area.id for super_area in region2.super_areas]
            assert len(super_area1_ids) == len(super_area2_ids)
            assert set(super_area1_ids) == set(super_area2_ids)
            region1_super_areas = [region1.super_areas[idx] for idx in np.argsort(super_area1_ids)]
            region2_super_areas = [region2.super_areas[idx] for idx in np.argsort(super_area2_ids)]
            for superarea1, superarea2 in zip(region1_super_areas, region2_super_areas):
                assert superarea1.id == superarea2.id
                assert superarea1.name == superarea2.name
 
    def test__subgroups(self, full_world, full_world_loaded):
        for person1, person2 in zip(full_world.people, full_world_loaded.people):
            assert person1.area.id == person2.area.id
            assert (person1.area.coordinates == person2.area.coordinates).all()
            for subgroup1, subgroup2 in zip(
                person1.subgroups.iter(), person2.subgroups.iter()
            ):
                if subgroup1 is None:
                    assert subgroup2 is None
                    continue
                assert subgroup1.group.spec == subgroup2.group.spec
                assert subgroup1.group.id == subgroup2.group.id
                assert subgroup1.subgroup_type == subgroup2.subgroup_type

    def test__household_area(self, full_world, full_world_loaded):
        assert len(full_world_loaded.households) == len(full_world_loaded.households)
        for household, household2 in zip(
            full_world.households, full_world_loaded.households
        ):
            if household.area is not None:
                assert household.area.id == household2.area.id
            else:
                assert household2.area is None

    def test__school_area(self, full_world, full_world_loaded):
        assert len(full_world_loaded.schools) == len(full_world.schools)
        for school, school2 in zip(full_world.schools, full_world_loaded.schools):
            if school.area is not None:
                assert school.area.id == school2.area.id
            else:
                assert school2.super_area is None

    def test__work_super_area(self, full_world, full_world_loaded):
        has_super_area = False
        for p1, p2 in zip(full_world.people, full_world_loaded.people):
            if p1.work_super_area is None:
                assert p2.work_super_area is None
            else:
                has_super_area = True
                assert p1.work_super_area.id == p2.work_super_area.id
                assert p1.work_super_area == p1.primary_activity.group.super_area
                assert p2.work_super_area == p2.primary_activity.group.super_area
                assert p1.work_super_area.id == p2.primary_activity.group.super_area.id
                if p1.work_super_area.city is None:
                    assert p2.work_super_area.city is None
                else:
                    assert p1.work_super_area.city.id == p2.work_super_area.city.id
        assert has_super_area
        has_people = False
        for company1, company2 in zip(
            full_world.companies, full_world_loaded.companies
        ):
            for person1, person2 in zip(company1.people, company2.people):

                has_people = True
                assert person1.work_super_area is not None
                assert person2.work_super_area is not None
                assert person1.work_super_area == company1.super_area
                assert person2.work_super_area == company2.super_area
        assert has_people

    def test__super_area_city(self, full_world, full_world_loaded):
        has_city = False
        for sa1, sa2 in zip(full_world.super_areas, full_world_loaded.super_areas):
            if sa1.city is None:
                assert sa2.city is None
            else:
                has_city = True
                assert sa1.city.id == sa2.city.id
                assert sa1.city.name == sa2.city.name
            for city, closest_station in sa1.closest_station_for_city.items():
                assert city in sa2.closest_station_for_city
                assert sa2.closest_station_for_city[city].id == closest_station.id
        assert has_city

    def test__care_home_area(self, full_world, full_world_loaded):
        assert len(full_world_loaded.care_homes) == len(full_world_loaded.care_homes)
        for carehome, carehome2 in zip(
            full_world.care_homes, full_world_loaded.care_homes
        ):
            assert carehome.area.id == carehome2.area.id
            assert carehome.area.name == carehome2.area.name

    def test__company_super_area(self, full_world, full_world_loaded):
        for company1, company2 in zip(
            full_world.companies, full_world_loaded.companies
        ):
            assert company1.super_area.id == company2.super_area.id

    def test__university_super_area(self, full_world, full_world_loaded):
        for uni1, uni2 in zip(full_world.universities, full_world_loaded.universities):
            assert uni1.area.id == uni2.area.id
            assert uni1.super_area.id == uni2.super_area.id
            assert uni1.super_area.name == uni2.super_area.name

    def test__hospital_super_area(self, full_world, full_world_loaded):
        for h1, h2 in zip(full_world.hospitals, full_world_loaded.hospitals):
            assert h1.area.id == h2.area.id
            assert h1.super_area.id == h2.super_area.id
            assert h1.super_area.name == h2.super_area.name
            assert h1.region_name == h2.region_name

    def test__social_venues_super_area(self, full_world, full_world_loaded):
        for spec in ["pubs", "groceries", "cinemas"]:
            social_venues1 = getattr(full_world, spec)
            social_venues2 = getattr(full_world_loaded, spec)
            assert len(social_venues1) == len(social_venues2)
            for v1, v2 in zip(social_venues1, social_venues2):
                assert v1.area.id == v2.area.id
                assert v1.super_area.id == v2.super_area.id
                assert v1.super_area.name == v2.super_area.name

    def test__commute(self, full_world, full_world_loaded):
        assert len(full_world.city_transports) > 0
        assert len(full_world.inter_city_transports) > 0
        assert len(full_world.city_transports) == len(full_world_loaded.city_transports)
        assert len(full_world.inter_city_transports) == len(
            full_world_loaded.inter_city_transports
        )
        for city1, city2 in zip(full_world.cities, full_world_loaded.cities):
            assert city1.name == city2.name
            assert len(city1.commuter_ids) == len(city2.commuter_ids)
            assert city1.commuter_ids == city2.commuter_ids
            assert len(city1.stations) == len(city2.stations)
            assert city1.super_area.id == city2.super_area.id
            for station1, station2 in zip(city1.stations, city2.stations):
                assert station1.super_area.id == station2.super_area.id
                assert len(station1.commuter_ids) == len(station2.commuter_ids)
                assert station1.commuter_ids == station2.commuter_ids

    def test__household_residents(self, full_world, full_world_loaded):
        for h1, h2 in zip(full_world.households, full_world_loaded.households):
            assert len(h1.residents) == len(h2.residents)
            h1_resident_ids = np.array([p.id for p in h1.residents])
            h2_resident_ids = np.array([p.id for p in h2.residents])
            for p1, p2 in zip(np.sort(h1_resident_ids), np.sort(h2_resident_ids)):
                assert p1 == p2

    def test__closest_hospitals(self, full_world, full_world_loaded):
        for sa1, sa2 in zip(full_world.super_areas, full_world_loaded.super_areas):
            assert len(sa1.closest_hospitals) == len(sa2.closest_hospitals)
            for h1, h2 in zip(sa1.closest_hospitals, sa2.closest_hospitals):
                assert h1.id == h2.id

    def test__social_venues(self, full_world, full_world_loaded):
        for area1, area2 in zip(full_world.areas, full_world_loaded.areas):
            for key in area1.social_venues.keys():
                assert key in area2.social_venues.keys()
                social_venues = area1.social_venues[key]
                social_venues_recovered = area2.social_venues[key]
                social_venues_id = np.sort([sv.id for sv in social_venues])
                social_venues_recovered_id = np.sort(
                    [sv.id for sv in social_venues_recovered]
                )
                assert np.array_equal(social_venues_id, social_venues_recovered_id)
        for h1, h2 in zip(full_world.households, full_world_loaded.households):
            if h1.households_to_visit is None:
                assert h2.households_to_visit is None
                continue
            assert len(h1.households_to_visit) == len(h2.households_to_visit)
            if h1.care_homes_to_visit is None:
                assert h2.care_homes_to_visit is None
                continue
            assert len(h1.care_homes_to_visit) == len(h2.care_homes_to_visit)
            if len(h1.households_to_visit) > 0:
                h1ids = np.sort([relative.id for relative in h1.households_to_visit])
                h2ids = np.sort([relative.id for relative in h2.households_to_visit])
                assert np.array_equal(h1ids, h2ids)
            if len(h1.care_homes_to_visit) > 0:
                h1ids = np.sort([relative.id for relative in h1.care_homes_to_visit])
                h2ids = np.sort([relative.id for relative in h2.care_homes_to_visit])
                assert np.array_equal(h1ids, h2ids)
