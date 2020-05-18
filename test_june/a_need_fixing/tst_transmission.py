import sys

sys.path.append("../june")
import numpy as np
import os
import yaml

from infection import Infection
from infection_selector import InfectionSelector
from transmission import Transmission
from symptoms import Symptoms
from june.groups.people import Person


def distribute_values(config):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title(
        "10 exampels for lognormal distribution of transmission probability over time"
    )
    selector = InfectionSelector(config)
    times = np.arange(0.0, 20.0, 0.1)
    for i in range(10):
        infection = selector.make_infection(Person("test", 0, 10, 0, "M", 0, 0), 0)
        probs = []
        for t in times:
            probs.append(infection.transmission_probability(t))
        ax.plot(times, probs)
    plt.show()


def distribute_values_Constant(config):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 exampels for constant transmission probability over time")
    selector = InfectionSelector(config)
    times = np.arange(0.0, 20.0, 0.1)
    for i in range(10):
        infection = selector.make_infection(Person("test", 0, 10, 0, "M", 0, 0), 0)
        probs = []
        for t in times:
            probs.append(infection.transmission_probability(t))
        ax.plot(times, probs)
    plt.show()


def distribute_values_XNExp(config):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 exampels for xnexp distribution over time")
    selector = InfectionSelector(config)
    times = np.arange(0.0, 20.0, 0.1)
    for i in range(10):
        infection = selector.make_infection(Person("test", 0, 10, 0, "M", 0, 0), 0)
        probs = []
        for t in times:
            probs.append(infection.transmission_probability(t))
        ax.plot(times, probs)
    plt.show()


if __name__ == "__main__":
    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "tests",
        "config_transmission_test.yaml",
    )
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    found = False

    if "distribute_values" in config:
        print("distribute values Gaussian shape")
        distribute_values(config["distribute_values"])
        found = True
    if "distribute_values_Constant" in config:
        print("distribute values tanh shape")
        distribute_values_Constant(config["distribute_values_Constant"])
        found = True
    if "distribute_values_XNExp" in config:
        print("distribute values xnexp shape")
        distribute_values_Constant(config["distribute_values_XNExp"])
        found = True
