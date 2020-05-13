import collections
import pytest
import numpy as np

from june.geography import Geography, Area
from june import demography as d


@pytest.fixture(name="area")
def area_name():
    return 
@pytest.fixture(name="geography_demography_test", scope="module")
def create_geography():
    return Geography.from_file(filter_key={"msoa" : ["E02004935"]})

def test__age_sex_generator():
    age_counts = [0, 2, 0, 2, 4]
    age_bins = [0, 3]
    female_fractions = [0, 1]
    age_sex_generator = d.demography.AgeSexGenerator(
        age_counts, age_bins, female_fractions
    )
    assert list(age_sex_generator.age_iterator) == [1, 1, 3, 3, 4, 4, 4, 4]
    assert list(age_sex_generator.sex_iterator) == [
        "m",
        "m",
        "f",
        "f",
        "f",
        "f",
        "f",
        "f",
    ]
    age_sex_generator = d.demography.AgeSexGenerator(
        age_counts, age_bins, female_fractions
    )
    ages = []
    sexes = []
    for _ in range(0, sum(age_counts)):
        age = age_sex_generator.age()
        sex = age_sex_generator.sex()
        ages.append(age)
        sexes.append(sex)

    assert sorted(ages) == [1, 1, 3, 3, 4, 4, 4, 4]
    assert collections.Counter(sexes) == collections.Counter(
        ["m", "m", "f", "f", "f", "f", "f", "f"]
    )

class TestDemography:
    def test__demography_for_areas(self):
        geography = Geography.from_file({"oa" : ["E00088544"]})
        area = list(geography.areas)[0]
        demography = d.Demography.for_areas(area_names=[area.name])
        area.populate(demography)
        population = area.people
        assert len(population) == 362
        people_ages_dict = {}
        people_sex_dict = {}
        for person in population:
            if person.age == 0:
                assert person.sex == 'f'
            if person.age > 90:
                assert person.sex == 'f'
            if person.age == 21:
                assert person.sex == 'm'
            if person.age not in people_ages_dict:
                people_ages_dict[person.age] = 1
            else:
                people_ages_dict[person.age] += 1
            if person.sex not in people_sex_dict:
                people_sex_dict[person.sex] = 1
            else:
                people_sex_dict[person.sex] += 1
        assert people_ages_dict[0] == 6
        assert people_ages_dict[71] == 3
        assert max(people_ages_dict.keys()) == 90

    def test__demography_for_super_areas(self):
        demography = d.Demography.for_zone(filter_key={"msoa" : ["E02004935"]})
        assert len(demography.age_sex_generators) == 26
    
    def test__demography_for_regions(self):
        demography = d.Demography.for_zone(filter_key={"region": ["North East"]})
        assert len(demography.age_sex_generators) == 8802
    
    def test__demography_for_geography(self, geography_demography_test):
        demography = d.Demography.for_geography(geography_demography_test)
        assert len(demography.age_sex_generators) == 26

class TestPopulation:
    def test__create_population_from_demography(self, geography_demography_test):
        demography = d.Demography.for_geography(geography_demography_test)
        population = list()
        for area in geography_demography_test.areas:
            area.populate(demography)
            population.extend(
                area.people
            )
        assert len(population) == 7602 
    
