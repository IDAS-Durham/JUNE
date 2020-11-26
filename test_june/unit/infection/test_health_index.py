import numpy as np
import pytest
from june.groups import CareHome
from june import paths
from june.groups import CareHome, Household
from june.demography import Person
from june.infection.health_index import HealthIndexGenerator, Data2Rates 


class TestHealthIndex():
    def test__probabilities_positive_sum_to_one(self,):
        data_to_rates = Data2Rates.from_file()
        health_index = HealthIndexGenerator(data_to_rates=data_to_rates)

        for population in ('care_home', 'general_population'):
            for sex in ('m', 'f'):
                for age in np.arange(100):
                    probabilities = health_index.outcome_probabilities[population][sex][age]
                    assert all(probabilities > 0)
                    assert sum(probabilities) == 1
    
    def test__right_probabilities(self,):
        data_to_rates = Data2Rates.from_file()
        health_index = HealthIndexGenerator(data_to_rates=data_to_rates)

        for population in ('care_home', 'general_population'):
            if population == 'care_home':
                is_care_home = True
            else:
                is_care_home = False
            for sex in ('m', 'f'):
                for age in np.arange(100):
                    probabilities = health_index.outcome_probabilities[population][sex][age]
                    assert probabilities[0] == health_index.asymptomatic_ratio
                    assert probabilities[2] == data_to_rates.get_hospital_infection_admission_rate(
                            age=age,sex=sex, is_care_home=is_care_home
                    )
                    assert probabilities[3] == data_to_rates.get_home_infection_fatality_rate(
                            age=age,sex=sex, is_care_home=is_care_home
                    )
                    assert probabilities[4] == data_to_rates.get_hospital_infection_fatality_rate(
                            age=age,sex=sex, is_care_home=is_care_home
                    )

