import numpy as np
import pandas as pd
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
    person = np.random.choice(list(box_random.people))
    assert hasattr(person, "health_index")

# tests of box based on census data
@pytest.fixture(name="box_region")
def create_box_for_region():
    #TODO takes awefully long
    box = BoxGenerator(region="test")
    return box


@pytest.fixture(name="inputs")
def get_input_data():
    inputs = Inputs(zone="test")
    n_residents = pd.read_csv(
        inputs.n_residents_file,
        names=["output_area", "counts"],
        header=0,
        index_col="output_area",
    )
    age_freq = pd.read_csv(inputs.age_freq_file, index_col="output_area")
    age_freq = age_freq.div(age_freq.sum(axis=1), axis=0)
    sex_freq = pd.read_csv(inputs.sex_freq_file, index_col="output_area")
    sex_freq = sex_freq.div(sex_freq.sum(axis=1), axis=0)
    #n_residents = n_residents.iloc[0]  # only one area is needed for testing
    #age_freq = age_freq[age_freq.index.isin([n_residents.name])]
    #sex_freq = sex_freq[sex_freq.index.isin([n_residents.name])]
    inputs = {
        "n_residents": n_residents["counts"],
        "age_freq": age_freq,
        "sex_freq": sex_freq
    }
    return inputs


def test__region_box_has_correct_number_of_people(box_region, inputs):
    true_people = inputs["n_residents"].values.sum()
    box_people = len(box_region.people)
    assert box_people == true_people
    assert box_region.n_people == true_people


def test__region_box_has_correct_sex_distribution(box_region, inputs):
    men = [person for person in box_region.people if person.sex == 0]
    women = [person for person in box_region.people if person.sex == 1]
    men_ratio = len(men) / box_region.n_people
    women_ratio = len(women) / box_region.n_people
    # census data
    number_of_men = (
        inputs["n_residents"].values * inputs["sex_freq"]["males"].values
    )
    number_of_men = int(number_of_men.sum())
    number_of_women = (
        inputs["n_residents"].values * inputs["sex_freq"]["females"].values
    )
    number_of_women = int(number_of_women.sum())
    total = number_of_men + number_of_women
    assert total == inputs["n_residents"].values.sum()
    true_men_ratio = number_of_men / total
    true_women_ratio = number_of_women / total
    assert np.isclose(men_ratio, true_men_ratio, atol=0, rtol=1e-2)
    assert np.isclose(women_ratio, true_women_ratio, atol=0, rtol=1e-2)

def test__region_box_has_correct_age_distribution(box_region, inputs):
    """
    Make a histogram of all ages in the box and compare it with
    the bin distribution from the nomis data.
    """
    age_counts = inputs["age_freq"]
    age_bins = age_counts.columns
    #age_counts_total = age_counts.mean(axis='columns').values * inputs["n_residents"].values
    age_counts_total = age_counts.mul(inputs["n_residents"].values, axis='rows')
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

def test__region_box_has_correct_health_index(box_region, inputs):
    """Need help testing this"""
    person = np.random.choice(list(box_region.people))
    assert hasattr(person, "health_index")


