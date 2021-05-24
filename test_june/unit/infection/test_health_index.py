import numpy as np
import pytest
from june.groups import CareHome
from june import paths
from june.groups import CareHome, Household
from june.infection.symptom_tag import SymptomTag
from june.demography import Person, Population
from june.infection.health_index import Data2Rates
from june.infection.health_index.health_index import (
    HealthIndexGenerator,
    index_to_maximum_symptoms_tag,
)
from june.interaction import Interaction


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


class TestMultipliers:
    def test__apply_multiplier(
        self,
    ):
        pass

    def test__comorbidities_effect(self):
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        dummy = Person.from_attributes(
            sex="f",
            age=60,
        )
        feo = Person.from_attributes(sex="f", age=60, comorbidity="feo")
        guapo = Person.from_attributes(sex="f", age=60, comorbidity="guapo")

        population = Population([])
        population.add(dummy)
        population.add(feo)
        population.add(guapo)

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
        interaction = Interaction(
            betas=None,
            alpha_physical=None,
            contact_matrices=None,
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=prevalence_reference_population,
            population=population,
        )
        health_index = HealthIndexGenerator.from_file()
        health_index.max_mild_symptom_tag = {
            value: key for key, value in index_to_maximum_symptoms_tag.items()
        }["severe"]
        dummy_health = health_index(dummy)
        feo_health = health_index(feo)
        guapo_health = health_index(guapo)

        mean_multiplier_uk = interaction.get_multiplier_from_reference_prevalence(
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
            * dummy_probabilities[2:].sum()
            / comorbidity_multipliers["no_condition"]
            * mean_multiplier_uk,
        )
        np.testing.assert_allclose(
            feo_probabilities[2:].sum(),
            comorbidity_multipliers["feo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum()
            / comorbidity_multipliers["no_condition"]
            * mean_multiplier_uk,
        )

        np.testing.assert_allclose(
            guapo_probabilities[:2].sum(),
            1
            - comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum()
            / comorbidity_multipliers["no_condition"]
            * mean_multiplier_uk,
        )
        np.testing.assert_allclose(
            guapo_probabilities[2:].sum(),
            comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum()
            / comorbidity_multipliers["no_condition"]
            * mean_multiplier_uk,
        )
        np.testing.assert_allclose(
            guapo_probabilities[:2].sum(),
            1
            - comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum()
            / comorbidity_multipliers["no_condition"]
            * mean_multiplier_uk,
        )
        np.testing.assert_allclose(
            guapo_probabilities[2:].sum(),
            comorbidity_multipliers["guapo"]
            / mean_multiplier_uk
            * dummy_probabilities[2:].sum()
            / comorbidity_multipliers["no_condition"]
            * mean_multiplier_uk,
        )
