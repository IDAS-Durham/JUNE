import sys
import numpy as np
import os
import yaml
from covid.time import Timer
from covid.infection import InfectionConstant
from covid.groups.people import Person
from covid.infection.symptoms.base import ALLOWED_SYMPTOM_TAGS


def test_trivial_check():
    timer = Timer(None)
    infection = InfectionConstant(None, timer)
    assert infection.symptoms.severity == 0.0


def test_symptom_tags(N=1000):
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
    np.testing.assert_allclose(tags,expected, atol=0.025)


if __name__ == "__main__":
    test_symptom_tags(10, )
