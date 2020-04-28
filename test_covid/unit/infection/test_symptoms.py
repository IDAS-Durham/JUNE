from covid.infection import symptons as sym

import numpy as np
import pytest


class TestSymptoms:
    def test__update_severity(self):

        symptom = sym.Symptoms(health_index=None)


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
