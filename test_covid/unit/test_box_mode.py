import numpy as np
import pytest
from covid.box_generator import BoxGenerator
from covid.inputs import Inputs
from covid.box_generator import get_age_brackets


# random box tests

@pytest.fixture(name="box_random")
def create_box_with_random_people():
    box = BoxGenerator(n_people=2000)
    return box


def test__random_box_has_correct_number_of_people(box_random):
    assert box_random.n_people == 2000
    assert len(box_random.people) == 2000


def test__random_box_has_correct_sex_distribution(box_random):
    men = [person for person in box_random.people if person.sex == 0]
    women = [person for person in box_random.people if person.sex == 1]
    assert np.isclose(len(men), len(women), atol=0, rtol=0.001)


def test__random_box_has_correct_age_distribution(box_random):
    all_ages = [person.age for person in box_random.people]
    _, counts = np.unique(all_ages, return_counts=True)
    mean_age_number = np.mean(counts)
    assert np.allclose(counts, mean_age_number, atol=0, rtol=0.1)


def test__random_box_has_correct_health_index_distribution(box_random):
    """Need help testing this"""
    person = np.random.choice(box_random.people)
    assert hasattr(person, "health_index")

# tests of box based on census data

@pytest.fixture(name="box_region")
def create_box_for_region():
    box = BoxGenerator(region="test", n_people=10)
    return box


@pytest.fixture(name="ne_inputs")
def get_north_east_ne_inputsut_data():
    ne_inputs = Inputs(zone="test")
    return ne_inputs


def test__region_box_has_correct_number_of_people(box_region, ne_inputs):
    true_people = ne_inputs.n_residents.values.sum()
    box_people = len(box_region.people)
    assert box_people == true_people
    assert box_region.n_people == true_people


def test__region_box_has_correct_sex_distribution(box_region, ne_inputs):
    men = [person for person in box_region.people if person.sex == 0]
    women = [person for person in box_region.people if person.sex == 1]
    men_ratio = len(men) / box_region.n_people
    women_ratio = len(women) / box_region.n_people
    # census data
    number_of_men = (
        ne_inputs.n_residents["n_residents"].values * ne_inputs.sex_freq["males"].values
    )
    number_of_men = int(number_of_men.sum())
    number_of_women = (
        ne_inputs.n_residents["n_residents"].values * ne_inputs.sex_freq["females"].values
    )
    number_of_women = int(number_of_women.sum())
    total = number_of_men + number_of_women
    assert total == ne_inputs.n_residents.values.sum()
    true_men_ratio = number_of_men / total
    true_women_ratio = number_of_women / total
    assert np.isclose(men_ratio, true_men_ratio, atol=0, rtol=1e-2)
    assert np.isclose(women_ratio, true_women_ratio, atol=0, rtol=1e-2)

def test__region_box_has_correct_age_distribution(box_region, ne_inputs):
    """
    Make a histogram of all ages in the box and compare it with
    the bin distribution from the nomis data.
    """
    age_counts = ne_inputs.age_freq
    age_bins = age_counts.columns
    age_counts_total = age_counts.values * ne_inputs.n_residents.values
    age_counts_total = age_counts_total.sum(axis=0).astype(np.int)
    nomis_bin_edges = []
    for bin in age_bins:
        age_1, age_2 = get_age_brackets(bin)
        nomis_bin_edges.append(age_1)
    nomis_bin_edges.append(age_2) #last limit
    ages_in_simulation = [person.age for person in box_region.people]
    ages_histogram, _ = np.histogram(ages_in_simulation, bins = nomis_bin_edges)
    assert(len(ages_histogram) == len(age_counts_total))
    assert(np.allclose(age_counts_total, ages_histogram, atol=0, rtol=1e-2))

def test__region_box_has_correct_health_index(box_region, ne_inputs):
    """Need help testing this"""
    person = np.random.choice(box_region.people)
    assert hasattr(person, "health_index")
