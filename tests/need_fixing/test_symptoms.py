import sys
import numpy as np
import os
import yaml
import pytest
from covid.time import Timer
from covid.infection import InfectionConstant
from covid.infection.symptoms import *
from covid.groups.people import Person
from covid.infection.symptoms.base import ALLOWED_SYMPTOM_TAGS


@pytest.fixture(name="user_parameters")
def make_user_parameters():
    user_parameters = {
        "Constant": {
            "recovery_rate": {
                "distribution": "constant",
                "parameters": {"value": 0.5,},
            }
        },
        "Gaussian": {
            "mean_time": {"distribution": "constant", "parameters": {"value": 2}},
            "sigma_time": {"distribution": "constant", "parameters": {"value": 3}},
        },
        "Tanh": {
            "max_time": {"distribution": "constant", "parameters": {"value": 2},},
            "onset_time": {"distribution": "constant", "parameters": {"value": 3}},
            "end_time": {"distribution": "constant", "parameters": {"value": 8}},
        },
    }

    return user_parameters


@pytest.mark.parametrize("symptom_type", ["Constant", "Step", "Gaussian", "Tanh"])
def test_read_parameters_default(symptom_type, test_timer):

    symptoms = globals()["Symptoms" + symptom_type](test_timer, None)
    for parameter in symptoms.required_parameters:
        assert hasattr(symptoms, parameter)


@pytest.mark.parametrize("symptom_type", ["Constant", "Step", "Gaussian", "Tanh"])
def test_read_parameters_user(symptom_type, user_parameters, test_timer):

    symptoms = globals()["Symptoms" + symptom_type](
        test_timer, None, user_parameters=user_parameters.get(symptom_type)
    )
    for parameter in user_parameters.get(symptom_type).keys():
        assert (
            getattr(symptoms, parameter)
            == user_parameters.get(symptom_type).get(parameter)["parameters"]["value"]
        )


@pytest.mark.parametrize("symptom_type", ["Step", "Gaussian", "Tanh"])
def test_update_severity(symptom_type, test_timer):
    """
    Check that severity starts from 0, and changes with time
    """
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]

    symptoms = globals()["Symptoms" + symptom_type](
            test_timer, health_index
    )

    assert symptoms.severity == 0.0

    while symptoms.timer.now < 3.0:
        next(symptoms.timer)
        symptoms.update_severity()
    assert symptoms.severity != 0.0


def test_symptom_tags(world_ne, test_timer, N=1000):
    """
    Check that ratio of symptoms matches input ratios after sampling
    """
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    infection = InfectionConstant(None, test_timer)
    severs1 = []
    tags = [0] * len(ALLOWED_SYMPTOM_TAGS)  # [0, 0, 0, 0, 0, 0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]

    person = Person(world_ne, 1, None, None, 1, 0, 1, health_index, None)
    for i in range(N):
        # reset timer
        infection.timer.day = 1
        infection.timer.day_int = 1
        infection.infect(person)
        while infection.timer.now < 3.0:
            next(infection.timer)
            person.infection.symptoms.update_severity()
        severity = person.infection.symptoms.severity
        severs1.append(severity)
        tag = person.infection.symptoms.tag
        tags[ALLOWED_SYMPTOM_TAGS.index(tag)] += 1

    for i in range(len(tags)):
        tags[i] = tags[i] / N
    np.testing.assert_allclose(tags, expected, atol=0.05)
