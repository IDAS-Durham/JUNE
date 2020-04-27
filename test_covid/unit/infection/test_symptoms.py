from covid.infection import symptons as sym

import pytest

class TestSymptoms:

    def test__update_severity(self):

        symptom = sym.Symptoms()

