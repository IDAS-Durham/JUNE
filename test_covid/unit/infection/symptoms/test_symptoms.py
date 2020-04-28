import sys
import numpy as np
import os
import yaml
import pytest
from covid.time import Timer
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
            "max_time": {"distribution": "constant", "parameters": {"value": 3},},
            "onset_time": {"distribution": "constant", "parameters": {"value": 1}},
            "end_time": {"distribution": "constant", "parameters": {"value": 8}},
        },
        "Step": {
            "time_offset": {"distribution": "constant", "parameters": {"value": 1},},
            "end_time": {"distribution": "constant", "parameters": {"value": 10},},
        }
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
def test_update_severity(symptom_type, test_timer, user_parameters):
    """
    Check that severity starts from 0, and updates
    """
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]

    symptoms = globals()["Symptoms" + symptom_type](
            test_timer, health_index, user_parameters = user_parameters.get(symptom_type)
    )
    assert symptoms.severity == 0.0
    symptoms.update_severity_at_time()
    assert symptoms.last_time_updated == test_timer.now


@pytest.mark.parametrize("symptom_type", ["Step", "Gaussian", "Tanh"])
def test_symptom_tags_have_right_frequency(symptom_type, user_parameters, world_ne, test_timer, N=500):
    """
    Check that ratio of symptoms matches input ratios after sampling
    """
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    tags = [0] * len(ALLOWED_SYMPTOM_TAGS)  # [0, 0, 0, 0, 0, 0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]

    for i in range(N):
        # Brute force reset timer ...
        test_timer.day = 1
        test_timer.day_int = 1
        symptoms = globals()["Symptoms" + symptom_type](
            test_timer, health_index, 
            user_parameters = user_parameters.get(symptom_type)
            )
        while symptoms.timer.now < 4.0:
            next(symptoms.timer)
            symptoms.update_severity_at_time()
        if symptoms.severity > 0:
            tag = symptoms.tag
            tags[ALLOWED_SYMPTOM_TAGS.index(tag)] += 1

    for i in range(len(tags)):
        tags[i] = tags[i] / N
    np.testing.assert_allclose(tags, expected, atol=0.1)
