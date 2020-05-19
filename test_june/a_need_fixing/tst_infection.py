import sys
from june.transmission import Transmission
from june.groups.people import Person
from june.infection import Infection
from june.infection_selector import InfectionSelector


def trivial_check(config):
    selector = InfectionSelector(config)
    infection = selector.make_infection(Person("test", 0, 10, 0, "M", 0, 0), 0)
    print("transmission parameters = ", config["infection"]["transmission"])
    print("   * Prob = ", infection.transmission_probability(1))


def distribute_value_Gamma(config1, config2):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    person = Person("test", 0, 10, 0, "M", 0, 0)

    selector1 = InfectionSelector(config1)
    probs1 = []
    for i in range(1000000):
        infection = selector1.make_infection(person, 0)
        probs1.append(infection.transmission_probability(1))

    selector2 = InfectionSelector(config2)
    probs2 = []
    for i in range(1000000):
        infection = selector2.make_infection(person, 0)
        probs2.append(infection.transmission_probability(1))

    fig, axes = plt.subplots()
    axes.hist(
        probs1,
        1000,
        range=(0, 5.0),
        density=True,
        facecolor="blue",
        alpha=0.5,
        label="$\\Gamma$($d^2$ = 4.$, $\\bar\\mu$ = 1.)",
    )
    axes.hist(
        probs2,
        1000,
        range=(0, 5.0),
        density=True,
        facecolor="red",
        alpha=0.5,
        label="$\\Gamma$($d^2$ = 1.$, $\\bar\\mu$ = 1.)",
    )
    plt.yscale("log")
    axes.set_ylim([0.001, 100.0])
    axes.legend()
    plt.show()


def distribute_value_Gauss(config1, config2):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()

    selector1 = InfectionSelector(config1)
    probs1 = []
    for i in range(1000000):
        infection = selector1.make_infection(Person("test", 0, 10, 0, "M", 0, 0), 0)
        probs1.append(infection.transmission_probability(1))

    probs2 = []
    selector2 = InfectionSelector(config2)
    for i in range(1000000):
        infection = selector2.make_infection(Person("test", 0, 10, 0, "M", 0, 0), 0)
        probs2.append(infection.transmission_probability(1))

    axes.hist(
        probs1,
        1000,
        range=(0, 1),
        density=True,
        facecolor="blue",
        alpha=0.5,
        label="symmetric, width = 0.3",
    )
    axes.hist(
        probs2,
        1000,
        range=(0, 1),
        density=True,
        facecolor="red",
        alpha=0.5,
        label="symmetric, widths = 0.1, 0.2",
    )
    axes.legend()
    plt.show()


if __name__ == "__main__":
    import os
    import yaml

    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "tests",
        "config_infection_test.yaml",
    )
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    found = False

    """
    if "trivial_check" in config:
        print ("trivial check")
        trivial_check(config["trivial_check"])
        found = True        
    """
    if "distribute_value_Gamma1" in config and "distribute_value_Gamma2" in config:
        print("gamma distribution")
        distribute_value_Gamma(
            config["distribute_value_Gamma1"], config["distribute_value_Gamma2"]
        )
        found = True
    """
    if ("distribute_value_Gauss1" in config and
        "distribute_value_Gauss2" in config):
        print ("gauss distribution")
        distribute_value_Gauss(config["distribute_value_Gauss1"],
                               config["distribute_value_Gauss2"])
        found = True
    """
    if not found:
        print("no keywords found:", config)
