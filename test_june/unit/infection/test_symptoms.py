import os

import autofit as af
import pytest

from june.infection import SymptomTag
from june.infection import symptoms as sym

directory = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session", autouse=True)
def do_something():
    af.conf.instance = af.conf.Config(config_path="{}/files/config/".format(directory))


class TestSymptoms:
    def test__tag__reads_from_symptoms_tag_using_severity(self):
        symptom = sym.Symptoms(health_index=None)
        symptom.severity = -0.1
        symptom.tag = symptom.make_tag()
        assert symptom.tag == SymptomTag.recovered

        symptom = sym.Symptoms(health_index=[0.1, 0.2, 0.3, 0.4, 0.5])

        symptom.severity = 0.01
        symptom.tag = symptom.make_tag()
        assert symptom.tag == SymptomTag.asymptomatic

        symptom.severity = 0.4
        symptom.tag = symptom.make_tag()
        assert symptom.tag == SymptomTag.hospitalised

        symptom.severity = 0.18
        symptom.tag = symptom.make_tag()
        assert symptom.tag == SymptomTag.influenza
