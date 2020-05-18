import sys
import numpy as np
import matplotlib.pyplot as plt

from june.groups import Group
from june.interaction import Interaction
from june.infection import Infection, InfectionSelector

def seed_infections(group, n_infections, selector):
    choices = np.random.choice(group.size(), n_infections)
    for choice in choices:
        group.people[choice].set_infection(selector.make_infection(group.people[choice], 0))
        

def get_groups(beta, mu, tau, N, times, mode, n_infections):
    Tparams = {}
    Tparams["Transmission:Type"] = "SIR"
    Tparams['Transmission:RecoverCutoff'] = {"Mean": tau}
    paramsP = {}
    Tparams["Transmission:Probability"] = paramsP
    paramsP["Mean"] = beta
    paramsR = {}
    Tparams["Transmission:Recovery"] = paramsR
    paramsR["Mean"] = mu
    selector = InfectionSelector(Tparams, None)
    group = Group("test", "Random", N)
    group.set_intensity(group.get_intensity() / group.size())
    #group.set_intensity(1)
    seed_infections(group, n_infections, selector)
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
    N    = 1000
    beta = 0.3
    mu   = 0.005
    tau  = 100000
    n_infections = 10
    times = np.arange(100)

    susceptible, infected, recovered = get_groups(beta, mu, tau, N, times, mode, n_infections)

    plt.figure()
    plt.plot(susceptible, label='Susceptible')
    plt.plot(infected, label='Infected')
    plt.plot(recovered, label='Recovered')
    plt.plot(np.sum([susceptible, infected, recovered], axis=0), label='Total')
    plt.legend()
    plt.show()
