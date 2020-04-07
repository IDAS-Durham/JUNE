import sys

sys.path.append("../covid")
from covid.transmission import Transmission
from covid.person import Person
from covid.infection import Infection
from covid.infection_selector import InfectionSelector


def trivial_check():
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = 0.5
    selector = InfectionSelector(Tparams, None)
    infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
    print("Tparams = ", Tparams)
    print("   * Prob = ", infection.transmission_probability(1))


def distribute_value_Gamma():
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()
    person = Person('test',0,10,'M',0,0)
    
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]  = "Gamma"
    params["Mean"]  = 1.0
    params["Shape"] = 0.25
    selector = InfectionSelector(Tparams, None)
    probs1 = []
    for i in range(1000000):
        infection = selector.make_infection(person,0)
        probs1.append(infection.transmission_probability(1))

    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]  = "Gamma"
    params["Mean"]  = 1.0
    params["Shape"] = 0.5
    probs2 = []
    selector = InfectionSelector(Tparams, None)
    for i in range(1000000):
        infection = selector.make_infection(person,0)
        probs2.append(infection.transmission_probability(1))

    axes.hist(
        probs1,
        1000,
        range=(0, 1),
        density=True,
        facecolor="blue",
        alpha=0.5,
        label="$\\Gamma(\\alpha = 0.25$, mean = 1.)",
    )
    axes.hist(
        probs2,
        1000,
        range=(0, 1),
        density=True,
        facecolor="red",
        alpha=0.5,
        label="$\\Gamma(\\alpha = 0.50$, mean = 1.)",
    )
    plt.yscale('log')
    axes.set_ylim([0.001,100.0])
    axes.legend()
    plt.show()

        
def distribute_value_Gauss():
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()

    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]      = "Gauss"
    params["Mean"]      = 0.5
    params["WidthPlus"] = 0.3
    params["Lower"]     = 0.0
    params["Upper"]     = 1.0

    selector = InfectionSelector(Tparams, None)
    probs1 = []
    for i in range(1000000):
        infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
        probs1.append(infection.transmission_probability(1))

    probs2 = []
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]       = "Gauss"
    params["Mean"]       = 0.5
    params["WidthPlus"]  = 0.2
    params["WidthMinus"] = 0.1
    params["Lower"]      = 0.0
    params["Upper"]      = 1.0
    selector = InfectionSelector(Tparams, None)
    for i in range(1000000):
        infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
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
    #trivial_check()
    #distribute_value_Gauss()
    distribute_value_Gamma()
