import numpy as np
import h5py
from collections import defaultdict
from itertools import count
from june.groups.leisure import generate_leisure_for_world, Pubs, Groceries, Cinemas
from june.demography import Demography, Person, Population
from june.demography.geography import Geography, Area, SuperArea
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
    save_commute_cities_to_hdf5,
    save_commute_hubs_to_hdf5,
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
    load_commute_cities_from_hdf5,
    load_commute_hubs_from_hdf5,
    load_universities_from_hdf5,
    load_social_venues_from_hdf5,
)
from june import paths

from pytest import fixture

class TestSavePeople:
    def test__save_population(self, full_world):
        population = full_world.people
        assert len(population) > 0
        save_population_to_hdf5(population, "test.hdf5")
        pop_recovered = load_population_from_hdf5("test.hdf5")
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
            # home city
            if person.home_city is None:
                assert person2.home_city is None
            else:
                assert person.home_city.id == person2.home_city


class TestSaveHouses:
    def test__save_households(self, full_world):
        households = full_world.households
        assert len(households) > 0
        save_households_to_hdf5(households, "test.hdf5")
        households_recovered = load_households_from_hdf5("test.hdf5")
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
        save_companies_to_hdf5(companies, "test.hdf5")
        companies_recovered = load_companies_from_hdf5("test.hdf5")
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
        save_hospitals_to_hdf5(hospitals, "test.hdf5")
        hospitals_recovered = load_hospitals_from_hdf5("test.hdf5")
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
        save_schools_to_hdf5(schools, "test.hdf5")
        schools_recovered = load_schools_from_hdf5("test.hdf5")
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
        save_care_homes_to_hdf5(carehomes, "test.hdf5")
        carehomes_recovered = load_care_homes_from_hdf5("test.hdf5")
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
        assert len(areas) > 0
        assert len(super_areas) > 0
        geography = Geography(areas, super_areas)
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


class TestSaveCommute:
    def test__save_cities(self, full_world):
        commute_cities = full_world.commutecities
        commute_city_units = full_world.commutecityunits
        assert len(commute_cities) > 0
        assert len(commute_city_units) > 0
        save_commute_cities_to_hdf5(commute_cities, "test.hdf5")
        (
            commute_cities_recovered,
            commute_city_units_recovered,
        ) = load_commute_cities_from_hdf5("test.hdf5")
        for city, city_recovered in zip(commute_cities, commute_cities_recovered):
            assert city.id == city_recovered.id
            for commute_hub, commute_hub_recovered in zip(
                city.commutehubs, city_recovered.commutehubs
            ):
                assert commute_hub.id == commute_hub_recovered

            for commute_internal, commute_internal_recovered in zip(
                city.commute_internal, city_recovered.commute_internal
            ):
                assert commute_internal.id == commute_internal_recovered
            for commute_city_unit, commute_city_unit_recovered in zip(
                city.commutecityunits, city_recovered.commutecityunits
            ):
                assert commute_city_unit.id == commute_city_unit_recovered.id
                assert commute_city_unit.city == commute_city_unit_recovered.city
                assert commute_city_unit.is_peak == commute_city_unit_recovered.is_peak
        for ccu1, ccu2 in zip(commute_city_units, commute_city_units_recovered):
            assert ccu1.id == ccu2.id

    def test__save_hubs(self, full_world):
        commute_hubs = full_world.commutehubs
        commute_units = full_world.commuteunits
        assert len(commute_hubs) > 0
        assert len(commute_units) > 0
        save_commute_hubs_to_hdf5(commute_hubs, "test.hdf5")
        commute_hubs_recovered, commute_units_recovered = load_commute_hubs_from_hdf5(
            "test.hdf5"
        )
        for hub, hub_recovered in zip(commute_hubs, commute_hubs_recovered):
            assert hub.id == hub_recovered.id
            assert hub.city == hub_recovered.city
            for commute_through, commute_through_recovered in zip(
                hub.commute_through, hub_recovered.commute_through
            ):
                assert commute_through.id == commute_through_recovered
            for person1, person2 in zip(hub.people, hub_recovered.people):
                assert person1.id == person2
            for unit1, unit2 in zip(hub.commuteunits, hub_recovered.commuteunits):
                assert unit1.id == unit2.id
                assert unit1.commutehub_id == unit2.commutehub_id
                assert unit1.city == unit2.city
        for cu1, cu2 in zip(commute_units, commute_units_recovered):
            assert cu1.id == cu2.id


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
            social_venues_list=[full_world.pubs, full_world.groceries, full_world.cinemas],
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
        world2 = generate_world_from_hdf5("test.hdf5")
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
            for area1, area2 in zip(super_area1.areas, super_area2.areas):
                assert area1.id == area2.id
                assert area1.super_area.id == area2.super_area.id
                assert area1.super_area.name == area2.super_area.name
                assert area1.name == area2.name

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

    def test__care_home_area(self, full_world, full_world_loaded):
        assert len(full_world_loaded.care_homes) == len(full_world_loaded.care_homes)
        for carehome, carehome2 in zip(full_world.care_homes, full_world_loaded.care_homes):
            assert carehome.area.id == carehome2.area.id
            assert carehome.area.name == carehome2.area.name

    def test__company_super_area(self, full_world, full_world_loaded):
        for company1, company2 in zip(full_world.companies, full_world_loaded.companies):
            assert company1.super_area.id == company2.super_area.id

    def test__university_super_area(self, full_world, full_world_loaded):
        for uni1, uni2 in zip(full_world.universities, full_world_loaded.universities):
            assert uni1.super_area.id == uni2.super_area.id
            assert uni1.super_area.name == uni2.super_area.name

    def test__hospital_super_area(self, full_world, full_world_loaded):
        for h1, h2 in zip(full_world.hospitals, full_world_loaded.hospitals):
            assert h1.super_area.id == h2.super_area.id
            assert h1.super_area.name == h2.super_area.name

    def test__social_venues_super_area(self, full_world, full_world_loaded):
        for spec in ["pubs", "groceries", "cinemas"]:
            social_venues1 = getattr(full_world, spec)
            social_venues2 = getattr(full_world_loaded, spec)
            assert len(social_venues1) == len(social_venues2)
            for v1, v2 in zip(social_venues1, social_venues2):
                assert v1.super_area.id == v2.super_area.id
                assert v1.super_area.name == v2.super_area.name

    def test__commute(self, full_world, full_world_loaded):
        assert len(full_world.commutecities) > 0
        assert len(full_world.commutecities) == len(full_world_loaded.commutecities)
        for city1, city2 in zip(full_world.commutecities, full_world_loaded.commutecities):
            assert city1.city == city2.city
            for hub1, hub2 in zip(city1.commutehubs, city2.commutehubs):
                assert hub1.id == hub2.id
            assert len(city1.commute_internal) == len(city2.commute_internal)
            for p1, p2 in zip(city1.commute_internal, city2.commute_internal):
                assert p1.id == p2.id

        assert len(full_world.commutehubs) > 0
        assert len(full_world.commutehubs) == len(full_world_loaded.commutehubs)
        for hub1, hub2 in zip(full_world.commutehubs, full_world_loaded.commutehubs):
            assert len(hub1.commute_through) == len(hub2.commute_through)
            for p1, p2 in zip(hub1.commute_through, hub2.commute_through):
                assert p1.id == p2.id
                assert p1.age == p2.age
                assert p1.sex == p2.sex

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
                h1ids = np.sort(
                    [relative.id for relative in h1.households_to_visit]
                )
                h2ids = np.sort(
                    [relative.id for relative in h2.households_to_visit]
                )
                assert np.array_equal(h1ids, h2ids)
            if len(h1.care_homes_to_visit) > 0:
                h1ids = np.sort(
                    [relative.id for relative in h1.care_homes_to_visit]
                )
                h2ids = np.sort(
                    [relative.id for relative in h2.care_homes_to_visit]
                )
                assert np.array_equal(h1ids, h2ids)
