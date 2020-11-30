import numpy as np
import pandas as pd
import yaml
from typing import Optional, List

from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from . import Data2Rates

_sex_short_to_long = {"m" : "male", "f" : "female"}

class HealthIndexGenerator:
    def __init__(
        self, data_to_rates: Data2Rates, asymptomatic_ratio: float = 0.2, max_age=99, age_bins=None
    ):
        self.data_to_rates = data_to_rates
        self.asymptomatic_ratio = asymptomatic_ratio
        self.outcome_probabilities = self._get_outcome_probabilities(max_age=max_age)
        self.age_bins = self._init_age_bins(age_bins, max_age)

    def _init_age_bins(self, age_bins, max_age):
        """
        Default binning is (0,5,10,15,...,90,99)
        """
        if age_bins is None:
            age_bins = [pd.Interval(left=agep, right=agep+4, closed="both") for agep in range(0, 90, 5)]
            age_bins.append(pd.Interval(left=90, right=max_age, closed="both"))
        return age_bins

    def __call__(self, person):
        """
        Computes the probability of having all 8 posible outcomes for all ages between 0 and 100,
        for male and female 
        """
        if person.residence is not None and person.residence.group.spec == "care_home":
            population = "care_home"
        else:
            population = "general_population"
        probabilities = self.outcome_probabilities[population][person.sex][person.age]
        return np.cumsum(probabilities)

    def _get_outcome_probabilities(self, max_age=99):
        n_outcomes = 6
        outcome_probabilities = {
            "care_home": {
                "m": np.zeros((max_age+1, n_outcomes)),
                "f": np.zeros((max_age+1, n_outcomes)),
            },
            "general_population": {
                "m": np.zeros((max_age+1, n_outcomes)),
                "f": np.zeros((max_age+1, n_outcomes)),
            },
        }
        for population in ("care_home", "general_population"):
            is_care_home = (population == "care_home")
            for sex in ["m", "f"]:
                _sex = _sex_short_to_long[sex]
                # values are constant at each bin
                for age_bin in self.age_bins:
                    hosp_admissions = self.data_to_rates.get_hospital_infection_admission_rate(
                        age=age_bin, sex=_sex, is_care_home=is_care_home
                    )
                    home_ifr = self.data_to_rates.get_home_infection_fatality_rate(
                        age=age_bin, sex=_sex, is_care_home=is_care_home
                    )
                    hosp_ifr = self.data_to_rates.get_hospital_infection_fatality_rate(
                        age=age_bin, sex=_sex, is_care_home=is_care_home
                    )
                    mild_cases = 1 - hosp_admissions - home_ifr 
                    # fill each age in bin
                    for age in range(age_bin.left, age_bin.right+1):
                        outcome_probabilities[population][sex][age][
                            0
                        ] = self.asymptomatic_ratio
                        outcome_probabilities[population][sex][age][1] = mild_cases
                        outcome_probabilities[population][sex][age][2] = hosp_admissions
                        outcome_probabilities[population][sex][age][3] = home_ifr
                        outcome_probabilities[population][sex][age][4] = hosp_ifr
        return outcome_probabilities

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
