from covid.infection import symptons as sym

import numpy as np
import pytest


class TestSymptoms:

    def test__tag__reads_from_symptoms_tag_using_severity(self):

        symptom = sym.Symptoms(health_index=None)

        symptom.severity = -0.1

        assert symptom.tag == "healthy"

        symptom = sym.Symptoms(health_index=[0.1, 0.2, 0.3, 0.4, 0.5])

        symptom.severity = 0.01

        assert symptom.tag in "asymptomatic"

        symptom.severity = 0.4

        assert symptom.tag in "hospitalised"

        symptom.severity = 0.18

        assert symptom.tag in "influenza-like illness"


class TestSymptomsConstant:
    def test__is_recovered__correct_depedence_on_recovery_rate(self):

        np.random.seed(1)

        symptom = sym.SymptomsConstant(health_index=None, recovery_rate=0.00001)

        assert symptom.is_recovered(deltat=1.0) == False
        assert symptom.is_recovered(deltat=10.0) == False

        symptom = sym.SymptomsConstant(health_index=None, recovery_rate=1000000.0)

        assert symptom.is_recovered(deltat=0.0001) == True
        assert symptom.is_recovered(deltat=1.0) == True

        symptom = sym.SymptomsConstant(health_index=None, recovery_rate=0.9)

        assert symptom.is_recovered(deltat=0.0) == False
        assert symptom.is_recovered(deltat=1.0) == True


class TestSymptomsGaussian:
    def test__update_severity__correct_depedence_on_parameters(self):

        np.random.seed(1)

        symptom = sym.SymptomsGaussian(
            health_index=None, start_time=0.0, mean_time=1.0, sigma_time=3.0
        )

        symptom.update_severity_at_time(time=0.0)

        # dt = 1.0
        # np.exp(-(1.0 ** 2) / 3.0 ** 2) = 0.89483

        assert symptom.severity == pytest.approx(symptom.maxseverity * 0.89483, 1.0e-4)
        assert symptom.last_time_updated == 0.0

        symptom = sym.SymptomsGaussian(
            health_index=None, start_time=1.0, mean_time=3.0, sigma_time=5.0
        )

        symptom.update_severity_at_time(time=2.0)

        # dt = 2.0 - (1.0 + 3.0)
        # np.exp(-(dt ** 2) / 5.0 ** 2)

        assert symptom.severity == pytest.approx(symptom.maxseverity * 0.85214, 1.0e-4)
        assert symptom.last_time_updated == 2.0


class TestSymptomsStep:
    def test__constructor__negatve_values_rounded_to_zero(self):

        symptom = sym.SymptomsStep(
            health_index=None, start_time=0.0, time_offset=-1.0, end_time=-2.0
        )

        assert symptom.time_offset == 0.0
        assert symptom.end_time == 0.0

    def test__update_severity__correct_dependence_on_parameters(self):

        symptom = sym.SymptomsStep(
            health_index=None, start_time=0.0, time_offset=1.0, end_time=2.0
        )

        symptom.update_severity_at_time(time=1.5)

        assert symptom.severity == symptom.maxseverity
        assert symptom.last_time_updated == 1.5

        symptom.update_severity_at_time(time=0.1)

        assert symptom.severity == 0.0
        assert symptom.last_time_updated == 0.1

        symptom.update_severity_at_time(time=10.0)

        assert symptom.severity == 0.0
        assert symptom.last_time_updated == 10.0


class TestSymptomsTanh:

    def test__constructor__negative_values_rounded_to_zero(self):

        symptom = sym.SymptomsTanh(
            health_index=None, start_time=-1.0, max_time=-1.0, onset_time=-1.0, end_time=-2.0
        )

        assert symptom.max_time == 0.0
        assert symptom.onset_time == 0.0
        assert symptom.end_time == 0.0

    def test__update_severity__correct_dependence_on_parameters(self):

        symptom = sym.SymptomsTanh(
            health_index=None, start_time=0.5, max_time=2.0, onset_time=0.5, end_time=15.0
        )

        # Time since start < max time
        # severity = 1.0 + np.tanh(3.14 * (time_since_start - self.onset_time) / self.delta_onset)) / 2.0
        # severity = (1.0 + np.tanh(3.14 * (1.0 - 0.5) / (2.0 - 0.5)) / 2.0

        symptom.update_severity_at_time(time=1.5)

        assert symptom.severity == pytest.approx(symptom.maxseverity * 0.890253, 1.0e-4)
        assert symptom.last_time_updated == 1.5

        # Time since start > max time
        # severity = 1.0 + np.tanh(3.14 * (end_time - time_since_start) / self.delta_end)) / 2.0
        # severity = (1.0 + np.tanh(3.14 * (15.0 - 2.5) / (15.0 - 2.0)) / 2.0

        symptom.update_severity_at_time(time=3.0)

        assert symptom.severity == pytest.approx(symptom.maxseverity * 0.997620, 1.0e-4)
        assert symptom.last_time_updated == 3.0

        # Time > end_time
        # severity = 0.0

        symptom.update_severity_at_time(time=10000.0)

        assert symptom.severity == 0.0
        assert symptom.last_time_updated == 10000.0