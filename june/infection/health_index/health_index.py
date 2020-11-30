import numpy as np
import pandas as pd
import yaml
from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from typing import Optional, List


class HealthIndexGenerator:
    def __init__(
        self, data_to_rates: "Data2Rates", asymptomatic_ratio: float = 0.2,
    ):
        self.data_to_rates = data_to_rates
        self.asymptomatic_ratio = asymptomatic_ratio
        self.outcome_probabilities = self.get_outcome_probabilities()

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

    def get_outcome_probabilities(self, n_outcomes=6, max_age=99):
        outcome_probabilities = {
            "care_home": {
                "m": np.zeros((max_age, n_outcomes)),
                "f": np.zeros((max_age, n_outcomes)),
            },
            "general_population": {
                "m": np.zeros((max_age, n_outcomes)),
                "f": np.zeros((max_age, n_outcomes)),
            },
        }

        for population in ("care_home", "general_population"):
            if population == "care_home":
                is_care_home = True
            else:
                is_care_home = False
            for sex in ["m", "f"]:
                if sex == "m":
                    _sex = "male"
                elif sex == "f":
                    _sex = "female"
                for age in np.arange(max_age):
                    hosp_admissions = self.data_to_rates.get_hospital_infection_admission_rate(
                        age=age, sex=_sex, is_care_home=is_care_home
                    )
                    icu_admissions = self.data_to_rates.get_icu_infection_admission_rate(
                        age=age, sex=_sex, is_care_home=is_care_home
                    )

                    home_ifr = self.data_to_rates.get_home_infection_fatality_rate(
                        age=age, sex=_sex, is_care_home=is_care_home
                    )
                    hosp_ifr = self.data_to_rates.get_hospital_infection_fatality_rate(
                        age=age, sex=_sex, is_care_home=is_care_home
                    )
                    icu_ifr = self.data_to_rates.get_icu_infection_fatality_rate(
                        age=age, sex=_sex, is_care_home=is_care_home
                    )

                    mild_cases = 1 - hosp_admissions - home_ifr #I deleated hosp_ifr from this line as i think it is inclouded in hosp_admissions
                    outcome_probabilities[population][sex][age][
                        0
                    ] = self.asymptomatic_ratio
                    outcome_probabilities[population][sex][age][1] = mild_cases
                    outcome_probabilities[population][sex][age][2] = hosp_admissions
                    outcome_probabilities[population][sex][age][3] = icu_admissions
                    outcome_probabilities[population][sex][age][3] = home_ifr
                    outcome_probabilities[population][sex][age][4] = hosp_ifr
                    outcome_probabilities[population][sex][age][5] = icu_ifr
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
