import pytest
from june.geography import Area
import numpy as np

from june import demography as d

#@pytest.fixture(name="demography", scope="session")
#def make_demography():
#    demography = d.Demography.for_areas(area_names=["E00088544"])
#    return demography

def test__demography_for_areas():
    demography = d.Demography.for_areas(area_names=["E00088544"])
    population = demography.population_for_area("E00088544")
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
    assert people_ages_dict[1] == 2
    assert people_ages_dict[45] == 4
    assert people_ages_dict[22] == 6
    assert people_ages_dict[71] == 3
    assert max(people_ages_dict.keys()) == 90

def test__demography_for_super_areas():
    demography = d.Demography.for_super_areas(["E02004935"])
    assert len(demography.age_sex_generators) == 26

def test__demography_for_regions():
    demography = d.Demography.for_regions(regions=["North East"])
    assert len(demography.age_sex_generators) == 8802
