from covid.infection import symptons as sym

import numpy as np
import pytest

class TestSymptoms:

    def test__update_severity(self):

        symptom = sym.Symptoms()


class TestSymptomsConstant:

    def test__is_recovered__gives_correct_probabaility(self):

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