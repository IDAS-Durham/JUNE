import sys
import numpy as np
import matplotlib.pyplot as plt

from covid.group import Group
from covid.interaction import Interaction
from covid.infection import Infection, InfectionSelector

def get_groups(beta, mu, N, times, mode):
    Tparams = {}
    Tparams["Transmission:Type"] = "SIR"
    paramsP = {}
    Tparams["Transmission:Probability"] = paramsP
    paramsP["Mean"] = beta
    paramsR = {}
    Tparams["Transmission:Recovery"] = paramsR
    paramsR["Mean"] = mu
    selector = InfectionSelector(Tparams, None)
    group = Group("test", "Random", N)
    group.set_intensity(group.get_intensity() / group.size())
    group.people[0].set_infection(selector.make_infection(group.people[0], 0))
    groups = []
    groups.append(group)
    interaction = Interaction(groups, 0, mode)

    susceptible = []
    infected = []
    recovered = []
    print("===============================================")
    for time in times:
        susceptible.append(group.size_susceptible())
        infected.append(group.size_infected())
        recovered.append(group.size_recovered())
        if time / 10 == int(time / 10):
            print('Time = {}, Susceptible = {}, Infected = {}, Recovered = {}'.format(time, group.size_susceptible(), group.size_infected(), group.size_recovered()))
        interaction.single_time_step(time, selector)
        group.update_status_lists(time)
    
    return susceptible, infected, recovered


if __name__ == "__main__":
    mode = 'Superposition'
    N = 1000
    beta = 0.05
    mu = 0.001
    times = np.arange(2000)

    susceptible, infected, recovered = get_groups(beta, mu, N, times, mode)

    plt.figure()
    plt.plot(susceptible, label='Susceptible')
    plt.plot(infected, label='Infected')
    plt.plot(recovered, label='Recovered')
    plt.plot(np.sum([susceptible, infected, recovered], axis=0), label='Total')
    plt.legend()
    plt.show()
