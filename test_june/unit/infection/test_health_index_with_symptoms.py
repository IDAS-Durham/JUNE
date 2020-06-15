import numpy as np
from collections import defaultdict
from june.demography.person import Person
from june.infection.symptoms import SymptomsStep
from june.infection.health_index import HealthIndexGenerator
from june.infection.symptoms import SymptomTag


def test__right_frequency_in_health_index():
    N_samples = 10000
    health_index = HealthIndexGenerator.from_file()(Person(age=60, sex="m"))

    frequencies = defaultdict(int)
    for _ in range(N_samples):
        symptoms = SymptomsStep(health_index=health_index, time_offset=0.0)
        symptoms.update_severity_from_delta_time(0.01)
        # check their symptoms matches the frequency in health index
        frequencies[symptoms.tag.name] += 1

    np.testing.assert_allclose(
        frequencies["asymptomatic"] / N_samples, health_index[0], atol=0.01
    )
    np.testing.assert_allclose(
        frequencies["influenza"] / N_samples,
        health_index[1] - health_index[0],
        atol=0.01,
    )
    np.testing.assert_allclose(
        frequencies["pneumonia"] / N_samples, health_index[2] - health_index[1], atol=0.01
    )
    np.testing.assert_allclose(
        frequencies["hospitalised"] / N_samples, health_index[3] - health_index[2], atol=0.01
    )
    np.testing.assert_allclose(
        frequencies["intensive_care"] / N_samples, health_index[4] - health_index[3], atol=0.01
    )
    np.testing.assert_allclose(frequencies["dead"] / N_samples, 1 - health_index[4], atol=0.01)
