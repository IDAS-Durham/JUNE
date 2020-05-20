import numpy as np
from june.demography.person import Person
from june.infection.symptoms import SymptomsStep
from june.infection.health_index import HealthIndexGenerator
from june.infection.symptoms import SymptomTags

def test__right_frequency_in_health_index():
    N_samples = 1000
    health_index = HealthIndexGenerator.from_file()(Person(age=27, sex='m'))

    frequencies = np.zeros(8)
    for i in range(N_samples):
        symptoms = SymptomsStep(health_index = health_index, time_offset=0.)
        symptoms.update_severity_from_delta_time(0.01)
        # check their symptoms matches the frequency in health index 
        if symptoms.tag != 'healthy':
            frequencies[SymptomTags(symptoms.tag) - 2] += 1

    np.testing.assert_allclose(frequencies[0]/N_samples, health_index[0], atol=0.05)
    np.testing.assert_allclose(frequencies[1]/N_samples, health_index[1]-health_index[0],
                               atol=0.05)
    np.testing.assert_allclose(frequencies[2]/N_samples, health_index[2]-health_index[1],
                               atol=0.05)
    np.testing.assert_allclose(frequencies[3]/N_samples, health_index[3]-health_index[2],
                               atol=0.05)
    np.testing.assert_allclose(frequencies[4]/N_samples, health_index[4]-health_index[3],
                               atol=0.05)
