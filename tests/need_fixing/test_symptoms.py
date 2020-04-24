import sys
import numpy as np
import os
import yaml
from covid.time import Timer
from covid.infection import InfectionConstant
from covid.infection.symptoms import *
from covid.groups.people import Person
from covid.infection.symptoms.base import ALLOWED_SYMPTOM_TAGS

def test_inputs_symptoms_constant():
    user_config = {
                'time_offset': 
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 15 ,
                    },
                },
                'end_time':
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 20 ,
                    },
                }

                }


    timer = Timer(None)
    sc = SymptomsConstant(timer, None, user_parameters = user_config)
    print(sc.time_offset)
    assert sc.time_offset == user_config['time_offset']['parameters']['value']
    assert sc.end_time == user_config['end_time']['parameters']['value']


def test_inputs_symptoms_tanh():
    user_config = {
                'max_time': 
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 2
                    },
                },
                'onset_time':
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 3 
                    }
                },
                'end_time':
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 8
                    }
                }

                }


    timer = Timer(None)
    sc = SymptomsTanh(timer, None, user_parameters=user_config)
    assert sc.max_time == user_config['max_time']['parameters']['value']
    assert sc.onset_time == user_config['onset_time']['parameters']['value']
    assert sc.end_time == user_config['end_time']['parameters']['value']



def test_inputs_symptoms_gaussian():
    user_config = {
                'mean_time': 
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 2
                    }
                },
                'sigma_time':
                {
                    'distribution': 'constant',
                    'parameters':
                    {
                        'value': 3 
                    }
                }

            }


    timer = Timer(None)
    sc = SymptomsGaussian(timer, None, user_parameters = user_config)
    assert sc.mean_time == user_config['mean_time']['parameters']['value']
    assert sc.sigma_time == user_config['sigma_time']['parameters']['value']


def test_update_severity():
    '''
    Check that severity starts from 0, and changes with time
    '''
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    symptoms_classes = [SymptomsConstant,
            SymptomsGaussian,
            SymptomsTanh,
            ]

    for symptom_type in symptoms_classes:
        timer = Timer(None)
        symptoms = symptom_type(timer, health_index)
        assert symptoms.severity == 0.0

        while symptoms.timer.now < 3.:
            next(symptoms.timer)
            symptoms.update_severity()
        assert symptoms.severity != 0.0



def test_symptom_tags(N=1000):
    '''
    Check that ratio of symptoms matches input ratios after sampling
    '''
    timer = Timer(None)
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    infection = InfectionConstant(None, timer)
    severs1 = []
    tags = [0]*len(ALLOWED_SYMPTOM_TAGS) #[0, 0, 0, 0, 0, 0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]

    person = Person(timer, 1, None, None, 1, 0, 1,health_index, None)
    for i in range(N):
        # reset timer
        infection.timer = Timer(None)
        infection.infect(person)
        while infection.timer.now < 3.:
            next(infection.timer)
            person.infection.symptoms.update_severity()
        severity = person.infection.symptoms.severity
        severs1.append(severity)
        tag = person.infection.symptoms.tag
        tags[ALLOWED_SYMPTOM_TAGS.index(tag)] += 1

    for i in range(len(tags)):
        tags[i] = tags[i] / N
    np.testing.assert_allclose(tags,expected, atol=0.05)


if __name__ == "__main__":
    test_update_severity()
