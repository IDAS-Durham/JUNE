import numpy as np
from june.demography import Demography, Person
from june.geography import Geography

from pytest import fixture


class TestSavePeople:
    @fixture(name="population")
    def make_population(self):
        geo = Geography.from_file({"oa": ["E00062339"]})
        dem = Demography.for_geography(geo)
        pop = dem.populate(geo.areas[0].name)
        return pop

    def test__save_population(self, population):
        population.to_hdf5("test.hdf5")
        pop_recovered = population.from_hdf5("test.hdf5")
        for person, person2 in zip(population, pop_recovered):
            for attribute_name in [
                "id",
                "age",
                "sex",
                "ethnicity",
                "area",
                "housemates",
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
            assert housemates == person2.housemates
