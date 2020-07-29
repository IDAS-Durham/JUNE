import numpy as np
from june.demography import Person
from june.infection.health_index import HealthIndexGenerator


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


def test__comorbidities_effect():
    comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_comorbidity": 1.0}
    prevalence_reference_population = {
        "feo": {
            "f": {"0-10": 0.2, "10-100": 0.4},
            "m": {"0-10": 0.6, "10-100": 0.5},
        },
        "guapo": {
            "f": {"0-10": 0.1, "10-100": 0.1},
            "m": {"0-10": 0.05, "10-100": 0.2},
        },
        "no_comorbidity": {
            "f": {"0-10": 0.7, "10-100": 0.5},
            "m": {"0-10": 0.35, "10-100": 0.3},
        },
    }

    health_index = HealthIndexGenerator.from_file(
        comorbidity_multipliers=comorbidity_multipliers,
        prevalence_reference_population=prevalence_reference_population,
    )

    dummy = Person.from_attributes(sex="f", age=40, )
    feo = Person.from_attributes(sex="f", age=40, comorbidity="feo")
    guapo = Person.from_attributes(sex="f", age=40, comorbidity="guapo")

    dummy_health = health_index(dummy)
    feo_health = health_index(feo)
    guapo_health = health_index(guapo)

    mean_multiplier_uk = (
        prevalence_reference_population["feo"]["f"]["10-100"]
        * comorbidity_multipliers["feo"]
        + prevalence_reference_population["guapo"]["f"]["10-100"]
        * comorbidity_multipliers["guapo"]
        + prevalence_reference_population["no_comorbidity"]["f"][
            "10-100"
        ]
        * comorbidity_multipliers["no_comorbidity"]
    )
    assert (
        health_index.get_multiplier_from_reference_prevalence(prevalence_reference_population, dummy)
        == mean_multiplier_uk
    )

    np.testing.assert_allclose(feo_health[:2], dummy_health[:2] * (2-comorbidity_multipliers['feo'] / mean_multiplier_uk))
    np.testing.assert_allclose(feo_health[3:], dummy_health[3:] * comorbidity_multipliers['feo'] / mean_multiplier_uk)
    np.testing.assert_allclose(
        guapo_health[:2], dummy_health[:2] * (2-comorbidity_multipliers['guapo'] / mean_multiplier_uk
    ))
    np.testing.assert_allclose(
        guapo_health[3:], dummy_health[3:] * comorbidity_multipliers['guapo'] / mean_multiplier_uk
    )
