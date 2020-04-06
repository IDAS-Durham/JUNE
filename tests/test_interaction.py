import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import covid.person as Person
import covid.group as Group
import covid.interaction as Interaction
import covid.infection as Infection
import covid.infection_selector as InfectionSelector


def ratio_SI_simulated(beta, N, N0, times, mode):
    """
    beta = transmission coefficient in units of 1/time
    N    = overall size of the group
    N0   = number of initially infected people
    mode = way to calculate transmission probability:
           - by adding beta = \sum_i beta_i ("Superposition"),
           - by multiplying no-infection probabilities ("Probabilistic")
    """
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params  = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = beta
    selector       = InfectionSelector.InfectionSelector(Tparams, None)
    group          = Group.Group("test", "Random", N)
    group.set_intensity(group.get_intensity() / group.size())
    for i in range(N0):
        group.people[i].set_infection(selector.make_infection(group.people[i], 0))
    groups = []
    groups.append(group)
    interaction = Interaction.Interaction(groups, 0, mode)
    ratio = []
    print("===============================================")
    for time in times:
        value = group.size_infected() / group.size()
        if time / 10 == int(time / 10):
            print(time, value)
        ratio.append(value)
        interaction.single_time_step(time, selector)
        group.update_status_lists(time)
    return ratio


def ratio_SI_analytic(beta, N, N0, times):
    """
    beta = transmission coefficient in units of 1/time
    N    = overall size of the group
    N0   = number of initially infected people
    """
    print("-----------------------------------------------")
    ratios = []
    for time in times:
        ratio = N0 / ((N - N0) * np.exp(-beta * time) + N0)
        if time / 10 == int(time / 10):
            print(time, ratio)
        ratios.append(ratio)
    return ratios

def ratio_SIR_numerical(beta, gamma, N, N0, times):
    """
    Numerical simulation of SIR model with simple Euler stepper in 10*times timesteps, 
    output are two ratios: infected/total (first list) and recovered/total (second list)
    beta  = transmission coefficient in units of 1/time
    gamma = recovery coefficient in units of 1/time
    N     = overall size of the group
    N0    = number of initially infected people
    """
    print("-----------------------------------------------")
    ratioI_by_N = []
    ratioR_by_N = []
    I = N0
    S = N-N0
    R = 0
    step = 10
    for time in times:
        for i in range(step):
            S = S - beta/step*S*I/N
            I = I + beta/step*S*I/N - gamma/step*I
            R = R + gamma/step*I
        ratioI = I/N
        ratioR = R/N
        if time / 10 == int(time / 10):
            print(time, ratioI, ratioR)
        ratioI_by_N.append(ratioI)
        ratioR_by_N.append(ratioR)
    return ratioI_by_N, ratioR_by_N

def test_SI():
    mode   = "Superposition"
    N      = 10000
    N0     = 100
    betas  = [0.050, 0.100, 0.150]
    cols   = ["steelblue", "royalblue", "navy"]
    simuls = []
    anals  = []
    diffs  = []
    times  = np.arange(100)
    for i in range(len(betas)):
        simul = ratio_SI_simulated(betas[i], N, N0, times, mode)
        anal  = ratio_SI_analytic(betas[i], N, N0, times)
        simuls.append(simul)
        anals.append(anal)
        diff = []
        for i in range(len(times)):
            diff.append(simul[i] / anal[i])
        diffs.append(diff)

    fig, axes = plt.subplots(2, 1, sharex=True)
    for i in range(len(betas)):
        beta  = betas[i]
        name = "$\\beta = $" + str(beta)
        axes[0].semilogy(times, simuls[i], label=name, color=cols[i])
        axes[0].semilogy(times, anals[i], color=cols[i], linestyle="dashed")
        axes[1].plot(times, diffs[i], color=cols[i])
        print(name)
    axes[0].legend()
    axes[0].set_ylabel("infected ratio")
    axes[0].set_yscale
    titlestring = "$N = "+str(N)+"$, $N_0 = "+str(N0)+"$ simulation vs SI model"
    axes[0].set_title(titlestring)
    axes[1].set_ylabel("simulation/analytic")
    axes[1].set_xlabel("time")
    fig.suptitle("Ratio of infected people (SI)")
    plt.show()

def test_SIR():
    N      = 10000
    N0     = 100
    betas  = [0.500, 0.500, 0.300]
    gammas = [0.100, 0.250, 0.100]
    colsI  = ["firebrick", "tomato", "darkred"]
    colsR  = ["steelblue", "royalblue", "navy"]
    styles = ["solid","dashed","dotted"]
    infN   = []
    recN   = []
    times  = np.arange(100)
    for i in range(len(betas)):
        beta  = betas[i]
        gamma = gammas[i]
        print ("beta = ",beta,", gamma = ",gamma)
        infected, recovered = ratio_SIR_numerical(beta, gamma, N, N0, times)
        infN.append(infected)
        recN.append(recovered)

    fig, axis = plt.subplots(1, 1, sharex=True)
    for i in range(len(betas)):
        beta  = betas[i]
        gamma = gammas[i]
        name  = "$\\beta = $" + str(beta)+", $\\gamma = $"+str(gamma)
        axis.plot(times, infN[i], label=name+": infected", color=colsI[i], linestyle=styles[i])
        axis.plot(times, recN[i], label=name+": recovered", color=colsR[i], linestyle=styles[i])
        print(name)
    fig.suptitle("Ratios of infected and recovered people (SIR)")
    plt.legend()
    plt.show()
    


if __name__ == "__main__":
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    test_SIR()

