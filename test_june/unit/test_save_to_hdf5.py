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
    )
from june.hdf5_savers import (
    load_geography_from_hdf5,
    load_population_from_hdf5,
    load_care_homes_from_hdf5,
    load_companies_from_hdf5,
    load_households_from_hdf5,
    load_population_from_hdf5,
    load_schools_from_hdf5,
    load_hospitals_from_hdf5
)

def clear_counters():
    SuperArea._id = count()
    Area._id = count()
    Group.__id_generators = defaultdict(count)

from pytest import fixture


@fixture(name="geography_h5", scope="module")
def make_geography():
    #clear_counters()
    geography = Geography.from_file({"msoa": ["E02006764", "E02003999", "E02002559"]})
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
    world = World(geography, demography, include_households=True)
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


class TestSaveHouses:
    def test__save_households(self, world_h5):
        households = world_h5.households
        save_households_to_hdf5(households, "test.hdf5")
        households_recovered = load_households_from_hdf5("test.hdf5")
        for household, household2 in zip(households, households_recovered):
            for attribute_name in ["id", "max_size", "communal"]:
                attribute = getattr(household, attribute_name)
                attribute2 = getattr(household2, attribute_name)
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
                "n_teachers",
                "n_teachers_max",
                "age_min",
                "age_max",
                "sector",
            ]:
                attribute = getattr(school, attribute_name)
                attribute2 = getattr(school2, attribute_name)
                print(attribute_name)
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
            for subgroup1, subgroup2 in zip(person1.subgroups.iter(), person2.subgroups):
                if subgroup1 is None:
                    assert subgroup2 is None
                    continue
                assert subgroup1.group.spec == subgroup2.group.spec
                assert subgroup1.group.id == subgroup2.group.id
                assert subgroup1.subgroup_type == subgroup2.subgroup_type

    def test__company_super_area(self, world_h5, world_h5_loaded):
        for company1, company2 in zip(world_h5.companies, world_h5_loaded.companies):
            assert company1.super_area.id == company2.super_area.id
