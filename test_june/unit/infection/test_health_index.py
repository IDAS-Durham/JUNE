import numpy as np
import pytest
from june.groups import CareHome
from june import paths
from june.groups import CareHome, Household
from june.demography import Person
from june.infection.health_index import Data2Rates
from june.infection.health_index.health_index import HealthIndexGenerator


@pytest.fixture(name="data_to_rates", scope="module")
def make_rates():
    return Data2Rates.from_file()


@pytest.fixture(name="health_index", scope="module")
def make_hi(data_to_rates):
    return HealthIndexGenerator(data_to_rates=data_to_rates)


class TestHealthIndex:
    def test__probabilities_positive_sum_to_one(self, health_index):
        for population in ("care_home", "general_population"):
            for sex in ("m", "f"):
                for age in np.arange(100):
                    cum_probs = health_index.cumulative_probabilities[population][sex][
                        age
                    ]
                    assert all(cum_probs > 0)
                    assert np.min(np.diff(cum_probs, prepend=0, append=1)) >= 0

    # class TestComorbidities:
    #    def test__mean_multiplier_reference(self, data_to_rates, health_index):
    #        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
    #        prevalence_reference_population = {
    #            "feo": {
    #                "f": {"0-10": 0.2, "10-100": 0.4},
    #                "m": {"0-10": 0.6, "10-100": 0.5},
    #            },
    #            "guapo": {
    #                "f": {"0-10": 0.1, "10-100": 0.1},
    #                "m": {"0-10": 0.05, "10-100": 0.2},
    #            },
    #            "no_condition": {
    #                "f": {"0-10": 0.7, "10-100": 0.5},
    #                "m": {"0-10": 0.35, "10-100": 0.3},
    #            },
    #        }
    #        data_to_rates.comorbidity_multipliers = comorbidity_multipliers
    #        data_to_rates.comorbidity_prevalence_reference_population = (
    #            prevalence_reference_population
    #        )
    #        dummy = Person.from_attributes(sex="f", age=40,)
    #
    #        mean_multiplier_uk = (
    #            prevalence_reference_population["feo"]["f"]["10-100"]
    #            * comorbidity_multipliers["feo"]
    #            + prevalence_reference_population["guapo"]["f"]["10-100"]
    #            * comorbidity_multipliers["guapo"]
    #            + prevalence_reference_population["no_condition"]["f"]["10-100"]
    #            * comorbidity_multipliers["no_condition"]
    #        )
    #        assert (
    #            health_index.get_multiplier_from_reference_prevalence(dummy.age, dummy.sex)
    #            == mean_multiplier_uk
    #        )

    """

    def test__comorbidities_effect(self):
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

        data_to_rates = Data2Rates.from_file()
        data_to_rates.comorbidity_multipliers = comorbidity_multipliers
        data_to_rates.comorbidity_prevalence_reference_population = prevalence_reference_population
        health_index = HealthIndexGenerator(data_to_rates)


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
    """
