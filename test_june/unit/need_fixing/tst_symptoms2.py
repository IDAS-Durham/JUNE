import sys
import random
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import itertools
import os
import yaml

from june.groups.people import Person
from june.groups.test_groups.test_group import TestGroups
from june.interaction import Interaction
from june.collective_interaction import CollectiveInteraction
from june.infection import Infection
from june.infection_selector import InfectionSelector


def check_symptoms():
    config = {}
    config["interaction"] = {}
    config["interaction"]["type"] = "collective"
    config["interaction"]["mode"] = "probabilistic"
    config["infection"] = {}
    config["infection"]["asymptomatic_ratio"] = 0.4
    config["infection"]["transmission"] = {}
    config["infection"]["transmission"]["type"] = "SI"
    config["infection"]["transmission"]["probability"] = {}
    config["infection"]["transmission"]["probability"]["mean"] = 0.0
    config["infection"]["symptoms"] = {}
    config["infection"]["symptoms"]["type"] = "Tanh"
    config["infection"]["symptoms"]["onset_time"] = {}
    config["infection"]["symptoms"]["onset_time"]["mean"] = 5.0
    config["infection"]["symptoms"]["max_time"] = {}
    config["infection"]["symptoms"]["max_time"]["mean"] = 10.0
    config["infection"]["symptoms"]["end_time"] = {}
    config["infection"]["symptoms"]["end_time"]["mean"] = 14.0
    selector = InfectionSelector(config)
    infection = selector.make_infection(
        Person("test", None, 40.0, 0, "F", [0.0, 0.5], 0), 0.0
    )
    times = np.arange(0.0, 20.0, 0.02)
    values = []
    for time in times:
        values.append(infection.symptom_severity(time))

    fig, axes = plt.subplots(1, 1, sharex=True)
    axes.plot(times, values)
    plt.show()


def make_config(beta):
    config = {}
    config["interaction"] = {}
    config["interaction"]["type"] = "collective"
    config["interaction"]["mode"] = "probabilistic"
    config["interaction"]["parameters"] = {}
    config["infection"] = {}
    config["infection"]["asymptomatic_ratio"] = 0.4
    config["infection"]["transmission"] = {}
    config["infection"]["transmission"]["type"] = "SI"
    config["infection"]["transmission"]["probability"] = {}
    config["infection"]["transmission"]["probability"]["mean"] = beta
    config["infection"]["symptoms"] = {}
    config["infection"]["symptoms"]["type"] = "Tanh"
    config["infection"]["symptoms"]["onset_time"] = {}
    config["infection"]["symptoms"]["onset_time"]["mean"] = 5.0
    config["infection"]["symptoms"]["onset_time"]["widthPlus"] = 2.0
    config["infection"]["symptoms"]["onset_time"]["lower"] = 3.0
    config["infection"]["symptoms"]["onset_time"]["upper"] = 8.0
    config["infection"]["symptoms"]["max_time"] = {}
    config["infection"]["symptoms"]["max_time"]["mean"] = 10.0
    config["infection"]["symptoms"]["max_time"]["widthPlus"] = 1.0
    config["infection"]["symptoms"]["max_time"]["lower"] = 8.0
    config["infection"]["symptoms"]["max_time"]["upper"] = 12.0
    config["infection"]["symptoms"]["end_time"] = {}
    config["infection"]["symptoms"]["end_time"]["mean"] = 14.0
    config["infection"]["symptoms"]["end_time"]["widthMinus"] = 1.0
    config["infection"]["symptoms"]["end_time"]["widthPlus"] = 2.0
    config["infection"]["symptoms"]["end_time"]["lower"] = 12.0
    config["infection"]["symptoms"]["end_time"]["upper"] = 21.0
    return config


def make_selector(config):
    return InfectionSelector(config)


def make_interaction(selector, config, groups):
    interaction = CollectiveInteraction(selector, config)
    interaction.set_groups([groups])
    return interaction


def check_infection_selector_for_ICmodel(selector, N, config):
    groups = TestGroups(people_per_group=N, total_people=N, config=config)
    group = groups.members[0]
    for i in range(N):
        group.people[i].set_infection(selector.make_infection(group.people[i], 0))
    return groups


def check_infection_progress(interaction, groups, endtime):
    group = groups.members[0]
    severities = []
    for person in group.people:
        severities.append(0.0)

    for time in range(1, endtime):
        # groups.members[0].output(False,True)
        interaction.set_time(time)
        interaction.time_step()
        for i in range(len(group.people)):
            severity = group.people[i].symptom_severity(time)
            if severity > severities[i]:
                severities[i] = severity
    N = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    Ndead = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    NICU = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    Nhosp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    NPneu = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    NILI = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    Nasymp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    for i in range(len(group.people)):
        age = group.people[i].get_age()
        index = min(7, int(age / 10))
        tag = group.people[i].get_infection().get_symptoms().tag(severities[i])
        N[index] += 1
        if tag == "asymptomatic":
            Nasymp[index] += 1
        elif tag == "influenza-like illness":
            NILI[index] += 1
        elif tag == "pneumonia":
            NPneu[index] += 1
        elif tag == "hospitalised":
            Nhosp[index] += 1
        elif tag == "intensive care":
            NICU[index] += 1
        elif tag == "dead":
            Ndead[index] += 1
    for i in range(len(N)):
        print(
            "Age: (",
            (i * 10),
            "-",
            ((i + 1) * 10 - 1),
            ": ",
            round(100.0 * Nasymp[i] / max(1, N[i]), 1),
            " % asymptomatic,",
            round(100.0 * NILI[i] / max(1, N[i]), 1),
            " % ILI,",
            round(100.0 * NPneu[i] / max(1, N[i]), 2),
            " % pneu.,",
            round(100.0 * Nhosp[i] / max(1, N[i]), 2),
            " % hosp.,",
            round(100.0 * NICU[i] / max(1, N[i]), 2),
            " % ICU,",
            round(100.0 * Ndead[i] / max(1, N[i]), 4),
            " % dead.",
        )


if __name__ == "__main__":
    # check_symptoms()
    N = 100000
    config = make_config(0.3)
    selector = make_selector(config)
    groups = check_infection_selector_for_ICmodel(selector, N, config)
    interaction = make_interaction(selector, config, groups)
    check_infection_progress(interaction, groups, 20)
