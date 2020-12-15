import numpy as np
import pandas as pd
import yaml
from typing import Optional, List

from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from . import Data2Rates

_sex_short_to_long = {"m": "male", "f": "female"}
index_to_maximum_symptoms_tag = {
    0: "asymptomatic",
    1: "mild",
    2: "severe",
    3: "hospitalised",
    4: "intensive_care",
    5: "dead_home",
    6: "dead_hospital",
    7: "dead_icu",
}


class HealthIndexGenerator:
    def __init__(
        self, data_to_rates: Data2Rates, max_age=99, age_bins=None, care_home_min_age=50
    ):
        self.data_to_rates = data_to_rates
        self.age_bins = self._init_age_bins(age_bins, max_age)
        self.care_home_min_age = care_home_min_age
        self.cumulative_probabilities = self._get_cumulative_probabilities(
            max_age=max_age
        )

    @classmethod
    def from_file(cls, max_age=99, age_bins=None, **kwarg):
        data_to_rates = Data2Rates.from_file(**kwarg)
        return cls(data_to_rates=data_to_rates, max_age=max_age, age_bins=age_bins)

    def _init_age_bins(self, age_bins, max_age):
        """
        Default binning is (0,5,10,15,...,90,99)
        """
        if age_bins is None:
            age_bins = [
                pd.Interval(left=agep, right=agep + 4, closed="both")
                for agep in range(0, 90, 5)
            ]
            age_bins.append(pd.Interval(left=90, right=max_age, closed="both"))
        return age_bins

    def __call__(self, person):
        """
        Computes the probability of having all 8 posible outcomes for all ages between 0 and 100,
        for male and female
        """
        if (
            person.residence is not None
            and person.residence.group.spec == "care_home"
            and person.age >= self.care_home_min_age
        ):
            population = "care_home"
        else:
            population = "general_population"
        cumulative_probabilities = self.cumulative_probabilities[population][
            person.sex
        ][person.age]
        return cumulative_probabilities

    def _set_cumulative_probability_per_age_bin(self, cp, age_bin, sex, population):
        _sex = _sex_short_to_long[sex]
        is_care_home = population == "care_home"
        hosp_admission_rate = self.data_to_rates.get_hospital_infection_admission_rate(
            age=age_bin, sex=_sex, is_care_home=is_care_home
        )
        icu_admission_rate = self.data_to_rates.get_icu_infection_admission_rate(
            age=age_bin, sex=_sex, is_care_home=is_care_home
        )
        home_ifr = self.data_to_rates.get_home_infection_fatality_rate(
            age=age_bin, sex=_sex, is_care_home=is_care_home
        )
        hosp_ifr = self.data_to_rates.get_hospital_infection_fatality_rate(
            age=age_bin, sex=_sex, is_care_home=is_care_home
        )
        icu_ifr = self.data_to_rates.get_icu_infection_fatality_rate(
            age=age_bin, sex=_sex, is_care_home=is_care_home
        )
        asymptomatic_rate = self.data_to_rates.get_asymptomatic_rate(
            age=age_bin, sex=_sex
        )
        mild_rate = self.data_to_rates.get_mild_rate(age=age_bin, sex=_sex)
        severe_rate = max(
            0,
            1 - (hosp_admission_rate + home_ifr + asymptomatic_rate + mild_rate),
        )
        # fill each age in bin
        for age in range(age_bin.left, age_bin.right + 1):
            cp[population][sex][age][0] = asymptomatic_rate  # recovers as asymptomatic
            cp[population][sex][age][1] = mild_rate  # recovers as mild
            cp[population][sex][age][2] = severe_rate  # recovers as severe
            cp[population][sex][age][3] = (
                hosp_admission_rate - hosp_ifr
            )  # recovers in the ward
            cp[population][sex][age][4] = max(
                icu_admission_rate - icu_ifr, 0
            )  # recovers in the icu
            cp[population][sex][age][5] = max(home_ifr, 0)  # dies at home
            cp[population][sex][age][6] = max(hosp_ifr - icu_ifr, 0)  # dies in the ward
            # cp[population][sex][age][7] = icu_ifr  # dies in the icu
            total = np.sum(cp[population][sex][age]) + icu_ifr
            cp[population][sex][age] = np.cumsum(cp[population][sex][age]) / total

    def _get_cumulative_probabilities(self, max_age=99):
        n_outcomes = 8
        cumulative_probabilities = {
            "care_home": {
                "m": np.zeros((max_age + 1, n_outcomes - 1)),
                "f": np.zeros((max_age + 1, n_outcomes - 1)),
            },
            "general_population": {
                "m": np.zeros((max_age + 1, n_outcomes - 1)),
                "f": np.zeros((max_age + 1, n_outcomes - 1)),
            },
        }
        for population in ("care_home", "general_population"):
            for sex in ["m", "f"]:
                # values are constant at each bin
                for age_bin in self.age_bins:
                    self._set_cumulative_probability_per_age_bin(
                        cp=cumulative_probabilities,
                        age_bin=age_bin,
                        sex=sex,
                        population=population,
                    )
        return cumulative_probabilities

    def get_multiplier_from_reference_prevalence(self, age, sex):
        """
        Compute mean comorbidity multiplier given the prevalence of the different comorbidities
        in the reference population (for example the UK). It will be used to remove effect of comorbidities
        in the reference population

        Parameters
        ----------
        prevalence_reference_population:
            nested dictionary with prevalence of comorbidity by comorbodity, age and sex cohort
        age:
            age group to compute average multiplier
        sex:
            sex group to compute average multiplier
        Returns
        -------
            weighted_multiplier:
                weighted mean of the multipliers given prevalence
        """
        weighted_multiplier = 0.0
        for (
            comorbidity
        ) in self.data_to_rates.comorbidity_prevalence_reference_population.keys():
            weighted_multiplier += (
                self.data_to_rates.comorbidity_multipliers[comorbidity]
                * self.data_to_rates.comorbidity_prevalence_reference_population[
                    comorbidity
                ][sex][age]
            )
        return weighted_multiplier
