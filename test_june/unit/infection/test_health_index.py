import numpy as np
import pytest
from june import paths
from june.groups import CareHome, Household
from june.demography import Person
from june.infection.health_index import HealthIndexGenerator, convert_comorbidities_prevalence_to_dict, read_comorbidity_csv


def test__smaller_than_one():
    index_list = HealthIndexGenerator.from_file()
    increasing_count = 0
    for i in range(len(index_list.prob_lists[0])):
        index_m = index_list(Person.from_attributes(age=i, sex="m"))
        index_w = index_list(Person.from_attributes(age=i, sex="f"))
        bool_m = np.sum(np.round(index_m, 7) <= 1)
        bool_w = np.sum(np.round(index_w, 7) <= 1)
        if bool_m + bool_w == 14:
            increasing_count += 1
        else:
            increasing_count == increasing_count
    assert increasing_count == 121


def test__non_negative_probability():
    probability_object = HealthIndexGenerator.from_file()
    probability_list = probability_object.prob_lists
    negatives = 0.0
    for i in range(len(probability_list[0])):
        negatives += sum(probability_list[0][i] < 0)
        negatives += sum(probability_list[1][i] < 0)
    assert negatives == 0


def test__growing_index():
    index_list = HealthIndexGenerator.from_file()
    increasing_count = 0
    for i in range(len(index_list.prob_lists[0])):
        index_m = index_list(Person.from_attributes(age=i, sex="m"))
        index_w = index_list(Person.from_attributes(age=i, sex="f"))

        if sum(np.sort(index_w) == index_w) != len(index_w):
            increasing_count += 0

        if sum(np.sort(index_m) == index_m) != len(index_m):
            increasing_count += 0

    assert increasing_count == 0

def test__parse_comorbidity_prevalence():
    male_filename = paths.data_path / 'input/demography/uk_male_comorbidities.csv'
    female_filename = paths.data_path / 'input/demography/uk_female_comorbidities.csv'
    prevalence_female = read_comorbidity_csv(female_filename)
    prevalence_male = read_comorbidity_csv(male_filename)
    for value in prevalence_female.sum(axis=1):
        assert value == pytest.approx(1.)
    for value in prevalence_male.sum(axis=1):
        assert value == pytest.approx(1.)

    prevalence_dict =  convert_comorbidities_prevalence_to_dict(prevalence_female, prevalence_male)
    assert prevalence_dict['sickle_cell']['m']['0-4'] == pytest.approx(3.92152E-05, rel=0.2)
    assert prevalence_dict['tuberculosis']['f']['4-9'] == pytest.approx(5.99818E-05, rel=0.2)
    assert prevalence_dict['tuberculosis']['f']['4-9'] == pytest.approx(5.99818E-05, rel=0.2)

def test__mean_multiplier_reference():
    comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
    prevalence_reference_population = {
        "feo": {"f": {"0-10": 0.2, "10-100": 0.4}, "m": {"0-10": 0.6, "10-100": 0.5},},
        "guapo": {
            "f": {"0-10": 0.1, "10-100": 0.1},
            "m": {"0-10": 0.05, "10-100": 0.2},
        },
        "no_condition": {
            "f": {"0-10": 0.7, "10-100": 0.5},
            "m": {"0-10": 0.35, "10-100": 0.3},
        },
    }
    health_index = HealthIndexGenerator.from_file(
        comorbidity_multipliers=comorbidity_multipliers,
        prevalence_reference_population=prevalence_reference_population,
    )

    dummy = Person.from_attributes(sex="f", age=40,)

    mean_multiplier_uk = (
        prevalence_reference_population["feo"]["f"]["10-100"]
        * comorbidity_multipliers["feo"]
        + prevalence_reference_population["guapo"]["f"]["10-100"]
        * comorbidity_multipliers["guapo"]
        + prevalence_reference_population["no_condition"]["f"]["10-100"]
        * comorbidity_multipliers["no_condition"]
    )
    assert (
        health_index.get_multiplier_from_reference_prevalence(
            dummy.age, dummy.sex
        )
        == mean_multiplier_uk
    )


def test__comorbidities_effect():
    comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
    prevalence_reference_population = {
        "feo": {"f": {"0-10": 0.2, "10-100": 0.4}, "m": {"0-10": 0.6, "10-100": 0.5},},
        "guapo": {
            "f": {"0-10": 0.1, "10-100": 0.1},
            "m": {"0-10": 0.05, "10-100": 0.2},
        },
        "no_condition": {
            "f": {"0-10": 0.7, "10-100": 0.5},
            "m": {"0-10": 0.35, "10-100": 0.3},
        },
    }

    health_index = HealthIndexGenerator.from_file(
        comorbidity_multipliers=comorbidity_multipliers,
        prevalence_reference_population=prevalence_reference_population,
    )

    dummy = Person.from_attributes(sex="f", age=60,)
    feo = Person.from_attributes(sex="f", age=60, comorbidity="feo")
    guapo = Person.from_attributes(sex="f", age=60, comorbidity="guapo")
    dummy_health = health_index(dummy)
    feo_health = health_index(feo)
    guapo_health = health_index(guapo)
    
    mean_multiplier_uk =  health_index.get_multiplier_from_reference_prevalence(
            dummy.age, dummy.sex
            )

    dummy_probabilities = np.diff(dummy_health, prepend=0.,append=1.)
    feo_probabilities = np.diff(feo_health, prepend=0.,append=1.)
    guapo_probabilities = np.diff(guapo_health, prepend=0.,append=1.)

    np.testing.assert_allclose(
        feo_probabilities[:2].sum(),
        1-comorbidity_multipliers['feo']/mean_multiplier_uk * dummy_probabilities[2:].sum(),
    )
    np.testing.assert_allclose(
        feo_probabilities[2:].sum(),
        comorbidity_multipliers['feo']/mean_multiplier_uk * dummy_probabilities[2:].sum(),
    )

    np.testing.assert_allclose(
        guapo_probabilities[:2].sum(),
        1-comorbidity_multipliers['guapo']/mean_multiplier_uk * dummy_probabilities[2:].sum()
    )
    np.testing.assert_allclose(
        guapo_probabilities[2:].sum(),
        comorbidity_multipliers['guapo']/mean_multiplier_uk * dummy_probabilities[2:].sum()
    )
    np.testing.assert_allclose(
        guapo_probabilities[:2].sum(),
        1-comorbidity_multipliers['guapo']/mean_multiplier_uk * dummy_probabilities[2:].sum()
    )
    np.testing.assert_allclose(
        guapo_probabilities[2:].sum(),
        comorbidity_multipliers['guapo']/mean_multiplier_uk * dummy_probabilities[2:].sum()
    )

def test__apply_hospitalisation_correction():
 
    health_index = HealthIndexGenerator.from_file()
    adjusted_health_index = HealthIndexGenerator(
            hosp_cases = health_index.hosp_cases,
            icu_hosp=health_index.icu_hosp,
            death_hosp=health_index.death_hosp,
            asymptomatic_ratio=health_index.asymptomatic_ratio,
            male_care_home_ratios = [0]*60 + [0.15]*40,
            female_care_home_ratios = [0]*60 + [0.2]*40,
    ) # percent of people in age group that doesnt live in a care home
    dummy = Person.from_attributes(sex="f", age=45,)
    hi = health_index(dummy)
    adjusted_hi = adjusted_health_index(dummy)
    np.testing.assert_allclose(adjusted_hi, hi)
    
    care_home = CareHome()
    care_home_resident = Person.from_attributes(sex="f", age=80,)
    care_home.add(care_home_resident)
    hi = np.diff(health_index(care_home_resident), prepend=0., append=1.)
    adjusted_hi = np.diff(adjusted_health_index(care_home_resident), prepend=0., append=1.)
    np.testing.assert_allclose(adjusted_hi, hi)
    
    non_resident = Person.from_attributes(sex="f", age=80,)
    household = Household()
    household.add(non_resident)
    hi = np.diff(health_index(non_resident), prepend=0., append=1.)
    adjusted_hi = np.diff(adjusted_health_index(non_resident), prepend=0., append=1.)
    assert sum(adjusted_hi) == 1.
    assert adjusted_hi[3] == pytest.approx(hi[3]*0.9/(1-0.2), rel=0.01)
    assert adjusted_hi[4] == pytest.approx(hi[4]*0.9/(1-0.2), rel=0.01)
    assert adjusted_hi[5] == hi[5]
    assert adjusted_hi[6] == pytest.approx(hi[6]*0.9/(1-0.2), rel=0.01)
    assert adjusted_hi[7] == pytest.approx(hi[7]*0.9/(1-0.2), rel=0.01)

    non_resident = Person.from_attributes(sex="m", age=80,)
    household = Household()
    household.add(non_resident)
    hi = np.diff(health_index(non_resident), prepend=0., append=1.)
    adjusted_hi = np.diff(adjusted_health_index(non_resident), prepend=0., append=1.)
    assert sum(adjusted_hi) == 1.
    assert adjusted_hi[3] == pytest.approx(hi[3]*0.9/(1-0.15), rel=0.01)
    assert adjusted_hi[4] == pytest.approx(hi[4]*0.9/(1-0.15), rel=0.01)
    assert adjusted_hi[5] == hi[5]
    assert adjusted_hi[6] == pytest.approx(hi[6]*0.9/(1-0.15), rel=0.01)
    assert adjusted_hi[7] == pytest.approx(hi[7]*0.9/(1-0.15), rel=0.01)
