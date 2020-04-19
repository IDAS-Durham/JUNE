import sys
import numpy as np
import os
import yaml
from covid.world import World
from covid.time import Timer
from covid.infection import Infection
from covid.groups.people import Person


def test_trivial_check():
    world = World()
    infection = Infection(world.people.members[0], world.timer)
    assert infection.symptom_severity == 0.


#TODO: move plot and non-automatic tests to plot_tests folder
def distribute_values(world):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 examples for Gaussian evolution of symptom severity over time")
    infection = Infection(world.people.members[0], world.timer)
    for i in range(10):
        severities = []
        times = []
        infection.infect(world.people.members[i+1])
        while infection.timer.day <= infection.timer.total_days:
            severities.append(world.people.members[i+1].infection.symptom_severity)
            times.append(infection.timer.now)
            next(infection.timer)
        ax.plot(times,severities, label=f'Age = {world.people.members[i+1].age}')
        infection.timer = Timer(world.config['time'])
    plt.legend()
    plt.show()

def distribute_values_Tanh(world):
    import random
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(9, 4))
    ax.set_title("10 examples for plateau'ed evolution of symptom severity over time")
    #TODO: how do we set symtomps parameters from here ?? 
    infection = Infection(world.people.members[0], world.timer)

    for i in range(10):
        infection.infect(world.people.members[i+1])
        severities = []
        times = []
        while infection.timer.day <= infection.timer.total_days:
            severities.append(world.people.members[i+1].infection.symptom_severity)
            times.append(infection.timer.now)
            next(infection.timer)
        ax.plot(times,severities, label=f'Age = {world.people.members[i+1].age}')
        infection.timer = Timer(world.config['time'])
    plt.legend()
    plt.show()

def check_symptom_tags(N,world):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    infection = Infection(world.people.members[0], world.timer)

    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    severs1  = []
    tags     = [0,   0,    0,    0,    0,    0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]
    allowed  = ["none","influenza-like illness", "pneumonia",
                "hospitalised", "intensive care",
                "dead"]
    person = world.people.members[0]
    for i in range(N):
        person.health_index = health_index
        # reset timer
        infection.timer = Timer(world.config['time'])
        infection.infect(person)
        next(infection.timer)
        next(infection.timer)
        severity  = world.people.members[0].infection.symptom_severity
        severs1.append(severity)
        tag = world.people.members[0].infection.symptoms.tag
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
    world = World()
    #print ("distribute values Gaussian shape")
    #distribute_values(world)
    print ("distribute values tanh shape")
    distribute_values_Tanh(world)
    check_symptom_tags(100000,world)
