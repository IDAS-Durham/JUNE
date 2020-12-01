import collections
import pytest
import numpy as np

from june.geography import Geography
from june import demography as d
from june.demography import AgeSexGenerator


@pytest.fixture(name="area")
def area_name():
    return


@pytest.fixture(name="geography_demography_test", scope="module")
def create_geography():
    return Geography.from_file(filter_key={"super_area": ["E02004935"]})


def test__age_sex_generator():
    age_counts = [0, 2, 0, 2, 4]
    age_bins = [0, 3]
    female_fractions = [0, 1]
    ethnicity_age_bins = [0, 2, 4]
    ethnicity_groups = ["A1", "B2", "C3"]
    ethnicity_structure = [[2, 0, 0], [0, 0, 2], [0, 4, 0]]
    age_sex_generator = d.demography.AgeSexGenerator(
        age_counts,
        age_bins,
        female_fractions,
        ethnicity_age_bins,
        ethnicity_groups,
        ethnicity_structure,
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
    assert list(age_sex_generator.ethnicity_iterator) == [
                "A1", "A1", "C3", "C3", "B2", "B2", "B2", "B2"
            ]
    age_sex_generator = d.demography.AgeSexGenerator(
        age_counts,
        age_bins,
        female_fractions,
        ethnicity_age_bins,
        ethnicity_groups,
        ethnicity_structure,
    )
    ages = []
    sexes = []
    ethnicities = []
    for _ in range(0, sum(age_counts)):
        age = age_sex_generator.age()
        sex = age_sex_generator.sex()
        ethnicity = age_sex_generator.ethnicity()
        ages.append(age)
        sexes.append(sex)
        ethnicities.append(ethnicity)

    assert sorted(ages) == [1, 1, 3, 3, 4, 4, 4, 4]
    assert collections.Counter(sexes) == collections.Counter(
        ["m", "m", "f", "f", "f", "f", "f", "f"]
    )
    assert collections.Counter(ethnicities) == collections.Counter(
        ["A1", "A1", "C3", "C3", "B2", "B2", "B2", "B2"]
    )


class TestDemography:
    def test__demography_for_areas(self):
        geography = Geography.from_file({"area": ["E00088544"]})
        area = list(geography.areas)[0]
        demography = d.Demography.for_areas(area_names=[area.name])
        area.populate(demography)
        population = area.people
        assert len(population) == 362
        people_ages_dict = {}
        people_sex_dict = {}
        for person in population:
            if person.age == 0:
                assert person.sex == "f"
            if person.age > 90:
                assert person.sex == "f"
            if person.age == 21:
                assert person.sex == "m"
            if person.age in range(55, 69):
                assert person.ethnicity.startswith("A")
                assert person.ethnicity in ["A1", "A2", "A4"]
            assert person.ethnicity.startswith("D") is False
            assert person.area.socioeconomic_index == 0.59 # checked in new socioecon_index file.
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
        demography = d.Demography.for_zone(filter_key={"super_area": ["E02004935"]})
        assert len(demography.age_sex_generators) == 26

    def test__demography_for_geography(self, geography_demography_test):
        demography = d.Demography.for_geography(geography_demography_test)
        assert len(demography.age_sex_generators) == 26

    def test__age_sex_generator_from_bins(self):
        men_age_dict = {"0-10": 1000, "11-70": 2000, "71-99": 500}
        women_age_dict = {"0-10": 1500, "11-70": 1000, "71-99": 1000}
        age_sex_gen = AgeSexGenerator.from_age_sex_bins(men_age_dict, women_age_dict)
        people_number = sum(men_age_dict.values()) + sum(women_age_dict.values())
        ages = []
        sexes = []
        for _ in range(people_number):
            ages.append(age_sex_gen.age())
            sexes.append(age_sex_gen.sex())
        ages = np.array(ages)
        sexes = np.array(sexes)
        men_idx = sexes == "m"
        men_ages = ages[men_idx]
        women_ages = ages[~men_idx]
        _, men_counts = np.unique(
            np.digitize(men_ages, [0, 11, 71]), return_counts=True
        )
        _, women_counts = np.unique(
            np.digitize(women_ages, [0, 11, 71]), return_counts=True
        )
        np.testing.assert_allclose(
            men_counts / women_counts, [10 / 15, 20 / 10, 5 / 10], atol=0, rtol=0.05
        )

    def test__comorbidities_for_areas(self):
        geography = Geography.from_file({"area": ["E00088544"]})
        area = list(geography.areas)[0]
        demography = d.Demography.for_areas(area_names=[area.name])
        area.populate(demography)
        comorbidities = []
        for person in area.people:
            if person.comorbidity is not None:
                comorbidities.append(person.comorbidity)
        assert len(np.unique(comorbidities)) > 0

class TestPopulation:
    def test__create_population_from_demography(self, geography_demography_test):
        demography = d.Demography.for_geography(geography_demography_test)
        population = list()
        for area in geography_demography_test.areas:
            area.populate(demography)
            population.extend(area.people)
        assert len(population) == 7602
