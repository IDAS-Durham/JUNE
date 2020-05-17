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
            for group_id, subgroup_type, group_array in zip(
                group_ids, subgroup_types, person2.subgroups
            ):
                assert group_id == group_array[0]
                assert subgroup_type == group_array[1]
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
        for person, person2 in zip(households, households_recovered):
            for attribute_name in [
                "id",
                "area",
                "max_size",
                "communal"
            ]:
                attribute = getattr(person, attribute_name)
                attribute2 = getattr(person2, attribute_name)
                if attribute is None:
                    assert attribute2 == None
                else:
                    assert attribute == attribute2
