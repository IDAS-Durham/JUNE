import sys
import numpy as np
import os
import yaml
from june.world import World
from june.time import Timer
from june.infection import Infection
from june.groups.people import Person



# TODO: move plot and non-automatic tests to plot_tests folder
def distribute_values(world):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 examples for Gaussian evolution of symptom severity over time")
    infection = Infection(world.people.members[0], world.timer)
    for i in range(10):
        severities = []
        times = []
        infection.infect(world.people.members[i + 1])
        while infection.timer.day <= infection.timer.total_days:
            severities.append(world.people.members[i + 1].infection.symptom_severity)
            times.append(infection.timer.now)
            next(infection.timer)
        ax.plot(times, severities, label=f"Age = {world.people.members[i+1].age}")
        infection.timer = Timer(world.config["time"])
    plt.legend()
    plt.show()


def distribute_values_symptoms_Tanh(world):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 examples for plateau'ed evolution of symptom severity over time")
    user_config = {'transmission': {'type': 'Constant'},
                    'symptoms': {'type': 'tanh'},
                   }
    infection = Infection(world.people.members[0], world.timer,
                        user_config)

    for i in range(10):
        infection.infect(world.people.members[i + 1])
        severities = []
        times = []
        while infection.timer.day <= infection.timer.total_days:
            severities.append(world.people.members[i + 1].infection.symptom_severity)
            times.append(infection.timer.now)
            next(infection.timer)
        ax.plot(times, severities, label=f"Age = {world.people.members[i+1].age}")
        infection.timer = Timer(world.config["time"])
    plt.legend()
    plt.show()

def check_symptom_tags(N):
    import random
    import matplotlib
    import matplotlib.pyplot as plt


    timer = Timer(None)
    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    infection = InfectionConstant(None, timer)
    severs1 = []
    tags = [0, 0, 0, 0, 0, 0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]
    allowed = [
        "asymptomatic",
        "influenza-like illness",
        "pneumonia",
        "hospitalised",
        "intensive care",
        "dead",
    ]
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
        tags[allowed.index(tag)] += 1

    for i in range(len(tags)):
        tags[i] = tags[i] / N
    print(tags)
    print(expected)

    fig, axes = plt.subplots(2, 1)
    axes[0].hist(
        severs1,
        20,
        range=(0, 1),
        density=True,
        facecolor="blue",
        alpha=0.5,
        label="flat distribution of severity",
    )
    axes[0].legend(loc="lower left")
    axes[1].bar(
        allowed, tags, color="blue", alpha=0.5, label="severity tag distribution"
    )

    axes[1].scatter(
        allowed, expected, color="black", label="expected severity tag distribution"
    )
    plt.xticks(rotation=45)
    plt.show()


if __name__ == "__main__":
    world = World()
    print ("distribute values Gaussian shape")
    distribute_values(world)
    print("distribute values tanh shape")
    distribute_values_symptoms_Tanh(world)
    check_symptom_tags(1000, world)
 