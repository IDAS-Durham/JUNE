import sys
sys.path.append("../covid")
import numpy as np
import os
import yaml

from infection import Infection
from infection_selector import InfectionSelector
from transmission import Transmission
from symptoms import Symptoms
from covid.groups.people import Person


def trivial_check(config):
    selector  = InfectionSelector(config)
    infection = selector.make_infection(Person('test',0,10,0,'M',0,0),0)
    print("   * Symptom severity = ", infection.symptom_severity(1))


def distribute_values(config):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 examples for Gaussian evolution of symptom severity over time")
    selector = InfectionSelector(config)
    times    = np.arange(0.,20.,0.1)
    for i in range(10):
        infection = selector.make_infection(Person('test',0,10,0,'M',0,0),0)
        severities = []
        for t in times:
            severities.append(infection.symptom_severity(t))
        ax.plot(times,severities)
    plt.show()

def distribute_values_Tanh(config):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 examples for plateau'ed evolution of symptom severity over time")
    selector = InfectionSelector(config)
    times    = np.arange(0.,20.,0.1)
    for i in range(10):
        infection = selector.make_infection(Person('test',0,10,0,'M',0,0),0)
        severities = []
        for t in times:
            severities.append(infection.symptom_severity(t))
        ax.plot(times,severities)
    plt.show()

def check_symptom_tags(N,config):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    selector = InfectionSelector(config)

    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    severs1  = []
    tags     = [0,   0,    0,    0,    0,    0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]
    allowed  = ["none","influenza-like illness", "pneumonia",
                "hospitalised", "intensive care",
                "dead"]
    for i in range(N):
        person    = Person('test',0,10,0,'M',health_index,0)
        infection = selector.make_infection(person,0)
        person.set_infection(infection)
        severity  = infection.symptom_severity(1)
        severs1.append(severity)
        tag = person.get_symptoms_tag(severity)
        for j in range(0,len(allowed)):
            if tag==allowed[j]:
                tags[j] += 1
                break
    for i in range(len(tags)):
        tags[i] = tags[i]/N
    print (tags)
        
    fig, axes = plt.subplots(2,1)
    axes[0].hist(severs1,20,range=(0, 1),
        density=True,facecolor="blue",alpha=0.5,
        label="flat distribution of severity",
    )
    axes[0].legend(loc='lower left')
    axes[1].bar(allowed,tags,
                color="blue",alpha=0.5,
                label="severity tag distribution")
    axes[1].scatter(allowed,expected,
                    color="black",
                    label="expected severity tag distribution")
    plt.show()


if __name__ == "__main__":
    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "tests",
        "config_symptoms_test.yaml",
    )
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    found = False

    if "trivial_check" in config:
        print ("trivial check")
        print (config["trivial_check"])
        trivial_check(config["trivial_check"])
        found = True        
    if "distribute_values" in config:
        print ("distribute values Gaussian shape")
        distribute_values(config["distribute_values"])
        found = True        
    if "distribute_values_Tanh" in config:
        print ("distribute values tanh shape")
        distribute_values_Tanh(config["distribute_values_Tanh"])
        found = True        
    if "symptoms_tag_test" in config:
        print ("symptoms_tag_test")
        check_symptom_tags(1000000,config["symptoms_tag_test"])
        found = True
