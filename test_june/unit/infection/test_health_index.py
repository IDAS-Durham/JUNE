import numpy as np
import pytest
from june.groups import CareHome
from june import paths
from june.groups import CareHome, Household
from june.infection.symptom_tag import SymptomTag
from june.demography import Person
from june.infection.health_index import Data2Rates
from june.infection.health_index.health_index import HealthIndexGenerator, index_to_maximum_symptoms_tag


@pytest.fixture(name="health_index", scope="module")
def make_hi():
    return HealthIndexGenerator.from_file()


class TestHealthIndex:
    def test__probabilities_positive_sum_to_one(self, health_index):
        for population in ("gp", "ch"):
            for sex in ("m", "f"):
                for age in np.arange(100):
                    if population == "ch" and age < 50:
                        continue
                    probs = health_index.probabilities[population][sex][age]
                    assert all(probs >= 0)
                    assert sum(probs) == pytest.approx(1, rel=1.0e-2)


class TestComorbidities:
    def test__mean_multiplier_reference(self, health_index):
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        prevalence_reference_population = {
            "feo": {
                "f": {"0-10": 0.2, "10-100": 0.4},
                "m": {"0-10": 0.6, "10-100": 0.5},
            },
            "guapo": {
                "f": {"0-10": 0.1, "10-100": 0.1},
                "m": {"0-10": 0.05, "10-100": 0.2},
            },
            "no_condition": {
                "f": {"0-10": 0.7, "10-100": 0.5},
                "m": {"0-10": 0.35, "10-100": 0.3},
            },
        }
        health_index.use_comorbidities = True
        health_index.comorbidity_multipliers = comorbidity_multipliers
        health_index.comorbidity_prevalence_reference_population = health_index._parse_prevalence_comorbidities_in_reference_population(
            prevalence_reference_population
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
            health_index.get_multiplier_from_reference_prevalence(dummy.age, dummy.sex)
            == mean_multiplier_uk
        )

    def test__comorbidities_effect(self):
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        prevalence_reference_population = {
            "feo": {
                "f": {"0-10": 0.2, "10-100": 0.4},
                "m": {"0-10": 0.6, "10-100": 0.5},
            },
            "guapo": {
                "f": {"0-10": 0.1, "10-100": 0.1},
                "m": {"0-10": 0.05, "10-100": 0.2},
            },
            "no_condition": {
                "f": {"0-10": 0.7, "10-100": 0.5},
                "m": {"0-10": 0.35, "10-100": 0.3},
            },
        }

        health_index = HealthIndexGenerator.from_file()
        health_index.use_comorbidities = True
        health_index.comorbidity_multipliers = comorbidity_multipliers
        health_index.comorbidity_prevalence_reference_population = health_index._parse_prevalence_comorbidities_in_reference_population(
            prevalence_reference_population
        )
        health_index.max_mild_symptom_tag = {value: key for key, value in index_to_maximum_symptoms_tag.items()}['severe']

        dummy = Person.from_attributes(sex="f", age=60,)
        feo = Person.from_attributes(sex="f", age=60, comorbidity="feo")
        guapo = Person.from_attributes(sex="f", age=60, comorbidity="guapo")
        dummy_health = health_index(dummy)
        feo_health = health_index(feo)
        guapo_health = health_index(guapo)

        mean_multiplier_uk = health_index.get_multiplier_from_reference_prevalence(
            dummy.age, dummy.sex
        )

        dummy_probabilities = np.diff(dummy_health, prepend=0.0, append=1.0)
        feo_probabilities = np.diff(feo_health, prepend=0.0, append=1.0)
        guapo_probabilities = np.diff(guapo_health, prepend=0.0, append=1.0)

        np.testing.assert_allclose(
            feo_probabilities[:2].sum(),
            1
            - comorbidity_multipliers["feo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum(),
        )
        np.testing.assert_allclose(
            feo_probabilities[2:].sum(),
            comorbidity_multipliers["feo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum(),
        )

        np.testing.assert_allclose(
            guapo_probabilities[:2].sum(),
            1
            - comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum(),
        )
        np.testing.assert_allclose(
            guapo_probabilities[2:].sum(),
            comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum(),
        )
        np.testing.assert_allclose(
            guapo_probabilities[:2].sum(),
            1
            - comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum(),
        )
        np.testing.assert_allclose(
            guapo_probabilities[2:].sum(),
            comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum(),
        )
