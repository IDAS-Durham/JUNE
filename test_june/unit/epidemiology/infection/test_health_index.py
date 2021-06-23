import numpy as np
import pytest
from june.groups import CareHome
from june import paths
from june.interaction import Interaction
from june.groups import CareHome, Household
from june.epidemiology.infection.symptom_tag import SymptomTag
from june.epidemiology.infection.health_index.health_index import (
    HealthIndexGenerator,
    index_to_maximum_symptoms_tag,
)
from june.demography import Person, Population
from june.epidemiology.infection import Covid19, B117, ImmunitySetter 


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

    @pytest.mark.parametrize("multiplier",[1.5,0.5])
    def test__apply_large_multiplier(
        self, multiplier
    ):
        health_index = HealthIndexGenerator.from_file()
        probabilities = np.array([1./8]*8)
        modified_probabilities = health_index.apply_effective_multiplier(
                probabilities=probabilities,
                effective_multiplier=multiplier
        )
        assert modified_probabilities[0] == (1 - 6./8.*multiplier)/2.
        assert modified_probabilities[1] == (1 - 6./8.*multiplier)/2.
        for i in range(2,8):
            assert modified_probabilities[i] == 1./8.*multiplier


    def test__comorbidities_effect(self):
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        dummy = Person.from_attributes(
            sex="f",
            age=60,
        )
        dummy.infection = Covid19(None,None)
        feo = Person.from_attributes(sex="f", age=60, comorbidity="feo")
        feo.infection = Covid19(None,None)
        guapo = Person.from_attributes(sex="f", age=60, comorbidity="guapo")
        guapo.infection = Covid19(None,None)

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
        multiplier_setter = ImmunitySetter(
            multiplier_by_comorbidity = comorbidity_multipliers,
            comorbidity_prevalence_reference_population=prevalence_reference_population,
        )
        multiplier_setter.set_multipliers(population)

        health_index = HealthIndexGenerator.from_file()
        health_index.max_mild_symptom_tag = {
            value: key for key, value in index_to_maximum_symptoms_tag.items()
        }["severe"]
        dummy_health = health_index(dummy, dummy.infection.infection_id())
        feo_health = health_index(feo, feo.infection.infection_id())
        guapo_health = health_index(guapo, guapo.infection.infection_id())

        mean_multiplier_uk = multiplier_setter.get_multiplier_from_reference_prevalence(
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
