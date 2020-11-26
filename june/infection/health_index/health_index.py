import numpy as np
import pandas as pd
import yaml
from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from typing import Optional, List

class HealthIndexGenerator:
    def __init__(
            self,
            data_to_rates: "Data2Rates",
            asymptomatic_ratio:float = 0.2,
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
            population = 'care_home'
        else:
            population = 'general_population'
        probabilities = self.outcome_probabilities[population][person.sex][person.age]
        return np.cumsum(probabilities)


    def get_outcome_probabilities(self, n_outcomes=6, max_age=100):
        outcome_probabilities = {
                'care_home': {'m': np.zeros(max_age,n_outcomes), 
                'f':np.zeros(max_age, n_outcomes)},
                'general_population': {'m': np.zeros(max_age,n_outcomes), 
                'f':np.zeros(max_age, n_outcomes)}
        }

        for population in ('care_home', 'general_population'):
            if population == 'care_home':
                is_care_home = True
            else:
                is_care_home = False
            for sex in ['m','f']:
                for age in np.range(max_age+1):
                    hosp_admissions = self.data_to_rates.get_hospital_infection_admission_rate(
                        age=age, sex=sex, is_care_home=is_care_home
                    )
                    home_ifr = self.data_to_rates.get_home_infection_fatality_rate(
                        age=age, sex=sex, is_care_home=is_care_home
                    )
                    hosp_ifr = self.data_to_rates.get_hospital_infection_fatality_rate(
                        age=age, sex=sex, is_care_home=is_care_home
                    )
                    mild_cases = 1 - hosp_admissions - home_ifr - hosp_ifr
                    outcome_probabilities[population][sex][age][0] = self.asymptomatic_ratio
                    outcome_probabilities[population][sex][age][1] =  mild_cases
                    outcome_probabilities[population][sex][age][2] =  hosp_admissions 
                    outcome_probabilities[population][sex][age][3] =  home_ifr 
                    outcome_probabilities[population][sex][age][4] =  hosp_ifr 
        return outcome_probabilities
