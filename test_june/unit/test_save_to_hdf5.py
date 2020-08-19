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


@fixture(name="geography_h5", scope="module")
def make_geography():
    geography = Geography.from_file(
        {"super_area": ["E02003282", "E02002559", "E02006887", "E02003034"]}
    )
    return geography


@fixture(name="world_h5", scope="module")
def create_world(geography_h5):
    with h5py.File("test.hdf5", "w"):
        pass  # reset file
    geography = geography_h5
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.universities = Universities.for_super_areas(geography.super_areas)
    world = generate_world_from_geography(
        geography=geography, include_households=True, include_commute=True
    )
    world.pubs = Pubs.for_geography(geography)
    world.cinemas = Cinemas.for_geography(geography)
    world.groceries = Groceries.for_geography(geography)
    leisure = generate_leisure_for_world(
        ["pubs", "cinemas", "groceries", "household_visits", "care_home_visits"], world
    )
    leisure.distribute_social_venues_to_households(
        households=world.households, super_areas=world.super_areas
    )
    return world


class TestSavePeople:
    def test__save_population(self, world_h5):
        population = world_h5.people
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
    def test__save_households(self, world_h5):
        households = world_h5.households
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
    def test__save_companies(self, world_h5):
        companies = world_h5.companies
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
    def test__save_hospitals(self, world_h5):
        hospitals = world_h5.hospitals
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
            if hospital.super_area is not None:
                assert hospital.super_area == hospital2.super_area
            else:
                assert hospital2.super_area is None
            assert hospital.coordinates[0] == hospital2.coordinates[0]
            assert hospital.coordinates[1] == hospital2.coordinates[1]
            assert hospital.trust_code == hospital2.trust_code


class TestSaveSchools:
    def test__save_schools(self, world_h5):
        schools = world_h5.schools
        save_schools_to_hdf5(schools, "test.hdf5")
        schools_recovered = load_schools_from_hdf5("test.hdf5")
        for school, school2 in zip(schools, schools_recovered):
            for attribute_name in [
                "id",
                "n_pupils_max",
                "age_min",
                "age_max",
                "sector",
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
    def test__save_carehomes(self, world_h5):
        carehomes = world_h5.care_homes
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
    def test__save_geography(self, world_h5):
        areas = world_h5.areas
        super_areas = world_h5.super_areas
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
    def test__save_cities(self, world_h5):
        commute_cities = world_h5.commutecities
        commute_city_units = world_h5.commutecityunits
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

    def test__save_hubs(self, world_h5):
        commute_hubs = world_h5.commutehubs
        commute_units = world_h5.commuteunits
        save_commute_hubs_to_hdf5(commute_hubs, "test.hdf5")
        commute_hubs_recovered, commute_units_recovered = load_commute_hubs_from_hdf5(
            "test.hdf5"
        )
        for hub, hub_recovered in zip(commute_hubs, commute_hubs_recovered):
            assert hub.id == hub_recovered.id
            assert hub.city == hub_recovered.city
            for person1, person2 in zip(hub.people, hub_recovered.people):
                assert person1.id == person2
            for unit1, unit2 in zip(hub.commuteunits, hub_recovered.commuteunits):
                assert unit1.id == unit2.id
                assert unit1.commutehub_id == unit2.commutehub_id
                assert unit1.city == unit2.city
        for cu1, cu2 in zip(commute_units, commute_units_recovered):
            assert cu1.id == cu2.id


class TestSaveUniversities:
    def test__save_universities(self, world_h5):
        universities = world_h5.universities
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
    def test__save_social_venues(self, world_h5):
        save_social_venues_to_hdf5(
            social_venues_list=[world_h5.pubs, world_h5.groceries, world_h5.cinemas],
            file_path="test.hdf5",
        )
        social_venues_dict = load_social_venues_from_hdf5("test.hdf5")
        for social_venues_spec, social_venues in social_venues_dict.items():
            for sv1, sv2 in zip(getattr(world_h5, social_venues_spec), social_venues):
                assert sv1.coordinates[0] == sv2.coordinates[0]
                assert sv1.coordinates[1] == sv2.coordinates[1]
                assert sv1.id == sv2.id


class TestSaveWorld:
    @fixture(name="world_h5_loaded", scope="module")
    def reaload_world(self, world_h5):
        world_h5.to_hdf5("test.hdf5")
        world2 = generate_world_from_hdf5("test.hdf5")
        return world2

    def test__save_geography(self, world_h5, world_h5_loaded):
        assert len(world_h5.areas) == len(world_h5_loaded.areas)
        for area1, area2 in zip(world_h5.areas, world_h5_loaded.areas):
            assert area1.id == area2.id
            assert area1.super_area.id == area2.super_area.id
            assert area1.super_area.name == area2.super_area.name
            assert area1.name == area2.name

        assert len(world_h5.super_areas) == len(world_h5_loaded.super_areas)
        for super_area1, super_area2 in zip(
            world_h5.super_areas, world_h5_loaded.super_areas
        ):
            assert super_area1.id == super_area2.id
            assert super_area1.name == super_area2.name
            for area1, area2 in zip(super_area1.areas, super_area2.areas):
                assert area1.id == area2.id
                assert area1.super_area.id == area2.super_area.id
                assert area1.super_area.name == area2.super_area.name
                assert area1.name == area2.name

    def test__subgroups(self, world_h5, world_h5_loaded):
        for person1, person2 in zip(world_h5.people, world_h5_loaded.people):
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

    def test__household_area(self, world_h5, world_h5_loaded):
        assert len(world_h5_loaded.households) == len(world_h5_loaded.households)
        for household, household2 in zip(
            world_h5.households, world_h5_loaded.households
        ):
            if household.area is not None:
                assert household.area.id == household2.area.id
            else:
                assert household2.area is None

    def test__school_area(self, world_h5, world_h5_loaded):
        assert len(world_h5_loaded.schools) == len(world_h5.schools)
        for school, school2 in zip(world_h5.schools, world_h5_loaded.schools):
            if school.area is not None:
                assert school.area.id == school2.area.id
            else:
                assert school2.super_area is None

    def test__care_home_area(self, world_h5, world_h5_loaded):
        assert len(world_h5_loaded.care_homes) == len(world_h5_loaded.care_homes)
        for carehome, carehome2 in zip(world_h5.care_homes, world_h5_loaded.care_homes):
            assert carehome.area.id == carehome2.area.id
            assert carehome.area.name == carehome2.area.name

    def test__company_super_area(self, world_h5, world_h5_loaded):
        for company1, company2 in zip(world_h5.companies, world_h5_loaded.companies):
            assert company1.super_area.id == company2.super_area.id

    def test__social_venues_super_area(self, world_h5, world_h5_loaded):
        for spec in ["pubs", "groceries", "cinemas"]:
            social_venues1 = getattr(world_h5, spec)
            social_venues2 = getattr(world_h5_loaded, spec)
            assert len(social_venues1) == len(social_venues2)
            for v1, v2 in zip(social_venues1, social_venues2):
                assert v1.super_area.id == v2.super_area.id
                assert v1.super_area.name == v2.super_area.name

    def test__commute(self, world_h5, world_h5_loaded):
        for city1, city2 in zip(world_h5.commutecities, world_h5_loaded.commutecities):
            assert city1.city == city2.city
            for hub1, hub2 in zip(city1.commutehubs, city2.commutehubs):
                assert hub1.id == hub2.id

        for hub1, hub2 in zip(world_h5.commutehubs, world_h5_loaded.commutehubs):
            people_in_hub1 = [person.id for person in hub1.people]
            people_in_hub2 = [person.id for person in hub2.people]
            if len(people_in_hub1) == 0 or len(people_in_hub2) == 0:
                assert len(people_in_hub2) == 0
                assert len(people_in_hub1) == 0
            else:
                assert (np.sort(people_in_hub1) == np.sort(people_in_hub2)).all()

    def test__household_residents(self, world_h5, world_h5_loaded):
        for h1, h2 in zip(world_h5.households, world_h5_loaded.households):
            assert len(h1.residents) == len(h2.residents)
            h1_resident_ids = np.array([p.id for p in h1.residents])
            h2_resident_ids = np.array([p.id for p in h2.residents])
            for p1, p2 in zip(np.sort(h1_resident_ids), np.sort(h2_resident_ids)):
                assert p1 == p2

    def test__social_venues(self, world_h5, world_h5_loaded):
        for p1, p2 in zip(world_h5.people, world_h5_loaded.people):
            if p1.residence.group.spec == "household":
                for key in p1.residence.group.social_venues.keys():
                    if key not in p2.residence.group.social_venues.keys():
                        assert len(p1.residence.group.social_venues[key]) == 0
                        continue
                    social_venues = p1.residence.group.social_venues[key]
                    social_venues_recovered = p2.residence.group.social_venues[key]
                    social_venues_id = np.sort([sv.id for sv in social_venues])
                    social_venues_recovered_id = np.sort(
                        [sv.id for sv in social_venues_recovered]
                    )
                    assert np.array_equal(social_venues_id, social_venues_recovered_id)
        for h1, h2 in zip(world_h5.households, world_h5_loaded.households):
            if h1.relatives_in_households is None:
                assert h2.relatives_in_households is None
                continue
            assert len(h1.relatives_in_households) == len(h2.relatives_in_households)
            if h1.relatives_in_care_homes is None:
                assert h2.relatives_in_care_homes is None
                continue
            assert len(h1.relatives_in_care_homes) == len(h2.relatives_in_care_homes)
            if len(h1.relatives_in_households) > 0:
                h1ids = np.sort(
                    [relative.id for relative in h1.relatives_in_households]
                )
                h2ids = np.sort(
                    [relative.id for relative in h2.relatives_in_households]
                )
                assert np.array_equal(h1ids, h2ids)
            if len(h1.relatives_in_care_homes) > 0:
                h1ids = np.sort(
                    [relative.id for relative in h1.relatives_in_care_homes]
                )
                h2ids = np.sort(
                    [relative.id for relative in h2.relatives_in_care_homes]
                )
                assert np.array_equal(h1ids, h2ids)
