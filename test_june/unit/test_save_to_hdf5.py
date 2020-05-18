import numpy as np
from june.demography import Demography, Person, Population
from june.geography import Geography
from june.groups import Households, Companies, Hospitals, Schools, CareHomes
from june.distributors import HouseholdDistributor
from june import World

from pytest import fixture

@fixture(name="geography_h5", scope="module")
def make_geography():
    geography = Geography.from_file({"msoa": ["E02006764"]})
    return geography


@fixture(name="world_h5", scope="module")
def create_world(geography_h5):
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
        population.to_hdf5("test.hdf5")
        pop_recovered = Population.from_hdf5("test.hdf5")
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
                    for subgroup in person.subgroups
                ]
            )
            group_ids = np.array(
                [
                    subgroup.group.id if subgroup is not None else None
                    for subgroup in person.subgroups
                ]
            )
            subgroup_types = np.array(
                [
                    subgroup.subgroup_type if subgroup is not None else None
                    for subgroup in person.subgroups
                ]
            )
            for group_spec, group_id, subgroup_type, group_array in zip(
                group_specs, group_ids, subgroup_types, person2.subgroups
            ):
                assert group_spec == group_array[0]
                assert group_id == group_array[1]
                assert subgroup_type == group_array[2]
            housemates = [mate.id for mate in person.housemates]
            assert housemates == list(person2.housemates)
            if person.area is not None:
                assert person.area.id == person2.area
            else:
                assert person2.area is None


class TestSaveHouses:
    def test__save_households(self, world_h5):
        households = world_h5.households
        households.to_hdf5("test.hdf5")
        households_recovered = Households.from_hdf5("test.hdf5")
        for household, household2 in zip(households, households_recovered):
            for attribute_name in [
                "id",
                "max_size",
                "communal"
            ]:
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
        companies.to_hdf5("test.hdf5")
        companies_recovered = Companies.from_hdf5("test.hdf5")
        for company, company2 in zip(companies, companies_recovered):
            for attribute_name in [
                "id",
                "n_workers_max",
                "sector"
            ]:
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
        hospitals.to_hdf5("test.hdf5")
        hospitals_recovered = Hospitals.from_hdf5("test.hdf5")
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
        schools.to_hdf5("test.hdf5")
        schools_recovered = schools.from_hdf5("test.hdf5")
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
        carehomes.to_hdf5("test.hdf5")
        carehomes_recovered = carehomes.from_hdf5("test.hdf5")
        for carehome, carehome2 in zip(carehomes, carehomes_recovered):
            for attribute_name in [
                "id",
                "n_residents"
            ]:
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
        geography.to_hdf5("test.hdf5")
        geography_recovered = Geography.from_hdf5("test.hdf5")
        for area, area2 in zip(areas, geography_recovered.areas):
            for attribute_name in [
                "id",
                "name"
            ]:
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

        for super_area, super_area2 in zip(super_areas, geography_recovered.super_areas):
            for attribute_name in [
                "id",
                "name"
            ]:
                attribute = getattr(super_area, attribute_name)
                attribute2 = getattr(super_area2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
            assert super_area.coordinates[0] == super_area2.coordinates[0]
            assert super_area.coordinates[1] == super_area2.coordinates[1]
