import sys

sys.path.append("../covid")
import transmission as Transmission
import infection as Infection


def trivial_check():
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = 0.5
    selector = Infection.InfectionSelector(Tparams, None)
    infection = selector.make_infection(0)
    print("Tparams = ", Tparams)
    print("   * Prob = ", infection.transmission_probability(1))


def distribute_value():
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()

    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = 0.5
    params["WidthPlus"] = 0.3
    params["Lower"] = 0.0
    params["Upper"] = 1.0

    selector = Infection.InfectionSelector(Tparams, None)
    probs1 = []
    for i in range(1000000):
        infection = selector.make_infection(0)
        probs1.append(infection.transmission_probability(1))

    probs2 = []
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = 0.5
    params["WidthPlus"] = 0.2
    params["WidthMinus"] = 0.1
    params["Lower"] = 0.0
    params["Upper"] = 1.0
    selector = Infection.InfectionSelector(Tparams, None)
    for i in range(1000000):
        infection = selector.make_infection(0)
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
    trivial_check()
    distribute_value()
