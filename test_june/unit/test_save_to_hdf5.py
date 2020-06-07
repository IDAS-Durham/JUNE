import numpy as np
import h5py
from collections import defaultdict
from itertools import count
from june.demography import Demography, Person, Population
from june.demography.geography import Geography, Area, SuperArea
from june.groups import Households, Companies, Hospitals, Schools, CareHomes, Group
from june.distributors import HouseholdDistributor
from june import World
from june.world import generate_world_from_hdf5
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
)

from pytest import fixture


@fixture(name="geography_h5", scope="module")
def make_geography():
    geography = Geography.from_file(
        #{"msoa": ["E02006764", "E02003999", "E02002559", "E02006887", "E02003034"]}
        {"msoa": ["E02003999", "E02002559", "E02006887", "E02003034"]}
    )
    return geography


@fixture(name="world_h5", scope="module")
def create_world(geography_h5):
    with h5py.File("test.hdf5", "w"):
        pass  # reset file
    geography = geography_h5
    demography = Demography.for_geography(geography)
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    world = World(geography, demography, include_households=True, include_commute=True)
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
                "sub_sector"
            ]:
                attribute = getattr(person, attribute_name)
                attribute2 = getattr(person2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2

            group_specs = np.array(
                [
                    subgroup.group.spec if subgroup is not None else None
                    for subgroup in person.subgroups.iter()
                ]
            )
            group_ids = np.array(
                [
                    subgroup.group.id if subgroup is not None else None
                    for subgroup in person.subgroups.iter()
                ]
            )
            subgroup_types = np.array(
                [
                    subgroup.subgroup_type if subgroup is not None else None
                    for subgroup in person.subgroups.iter()
                ]
            )
            for group_spec, group_id, subgroup_type, group_array in zip(
                group_specs, group_ids, subgroup_types, person2.subgroups
            ):
                assert group_spec == group_array[0]
                assert group_id == group_array[1]
                assert subgroup_type == group_array[2]
            if person.area is not None:
                assert person.area.id == person2.area
            else:
                assert person2.area is None

            # mode of transport
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
                if attribute_name == "type":
                    attribute2 = getattr(household2, attribute_name)
                else:
                    attribute2 = getattr(household2, attribute_name)
                attribute = getattr(household, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            if household.area is not None:
                assert household.area.id == household2.area
            else:
                assert household2.area is None


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
            if company.super_area is not None:
                assert company.super_area.id == company2.super_area
            else:
                assert company2.super_area is None
            

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
                assert hospital.super_area.id == hospital2.super_area
            else:
                assert hospital2.super_area is None
            assert hospital.coordinates[0] == hospital2.coordinates[0]
            assert hospital.coordinates[1] == hospital2.coordinates[1]
            


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
            if school.super_area is not None:
                assert school.super_area.id == school2.super_area
            else:
                assert school2.super_area is None
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
            if carehome.area is not None:
                assert carehome.area.id == carehome2.area
            else:
                assert carehome2.area is None
            

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
            if area.super_area is not None:
                assert area.super_area.id == area2.super_area
            else:
                assert area2.super_area is None
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
        save_commute_cities_to_hdf5(commute_cities, "test.hdf5")
        commute_cities_recovered = load_commute_cities_from_hdf5("test.hdf5")
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

    def test__save_hubs(self, world_h5):
        commute_hubs = world_h5.commutehubs
        save_commute_hubs_to_hdf5(commute_hubs, "test.hdf5")
        commute_hubs_recovered = load_commute_hubs_from_hdf5("test.hdf5")
        for hub, hub_recovered in zip(commute_hubs, commute_hubs_recovered):
            assert hub.id == hub_recovered.id
            assert hub.city == hub_recovered.city
            for person1, person2 in zip(hub.people, hub_recovered.people):
                assert person1.id == person2
            for unit1, unit2 in zip(hub.commuteunits, hub_recovered.commuteunits):
                assert unit1.id == unit2.id
                assert unit1.commutehub_id == unit2.commutehub_id
                assert unit1.city == unit2.city


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
            for subgroup1, subgroup2 in zip(
                person1.subgroups.iter(), person2.subgroups.iter()
            ):
                if subgroup1 is None:
                    assert subgroup2 is None
                    continue
                assert subgroup1.group.spec == subgroup2.group.spec
                assert subgroup1.group.id == subgroup2.group.id
                assert subgroup1.subgroup_type == subgroup2.subgroup_type

    def test__company_super_area(self, world_h5, world_h5_loaded):
        for company1, company2 in zip(world_h5.companies, world_h5_loaded.companies):
            assert company1.super_area.id == company2.super_area.id

    def test__commute(self, world_h5, world_h5_loaded):
        for hub1, hub2 in zip(world_h5.commutehubs, world_h5_loaded.commutehubs):
            for person1, person2 in zip(hub1.people, hub2.people):
                assert person1.id == person2.id
