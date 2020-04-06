import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import covid.person as Person
import covid.group as Group
import covid.interaction as Interaction
import covid.infection as Infection
import covid.infection_selector as InfectionSelector

def ratio_SI_simulated(beta, N, times, mode, I_0):
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params  = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = beta
    selector = InfectionSelector(Tparams, None)
    group = Group("test", "Random", N)
    if mode=='Superposition':
        group.set_intensity(group.get_intensity() / group.size())
    for i in range(I_0):
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


def ratio_SI_analytic(beta, N, times, I_0):
    print("-----------------------------------------------")
    ratios = []
    for time in times:
        ratio = I_0/ ((N - I_0) * np.exp(-beta * time) + I_0)
        if time / 10 == int(time / 10):
            print(time, ratio)
        ratios.append(ratio)
    return ratios

def ratio_SIR_numerical(beta, gamma, N, times, I_0):
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
    I = I_0
    S = N-I_0
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

def multi_run(I_0, N, times, betas_sim, betas_anal, nruns):

    simul_av = np.zeros((nruns, len(betas_sim), len(times)))
    diff_av = np.zeros((nruns, len(betas_sim), len(times)))
    for i in range(nruns):
        simuls = []
        anals = []
        diffs = []
        for beta_sim, beta_anal in zip(betas_sim, betas_anal):
            simul = ratio_SI_simulated(beta_sim, N, times, mode, I_0)
            anal = ratio_SI_analytic(beta_anal, N, times, I_0)
            simuls.append(simul)
            anals.append(anal)
            diff = []
            for j in range(len(times)):
                diff.append(simul[j] / anal[j])
            diffs.append(diff)
        simul_av[i] = np.array(simuls)
        diff_av[i] = np.array(diffs)
        

    return np.mean(simul_av, axis=0), np.std(simul_av, axis=0)/np.sqrt(nruns), anals, np.mean(diff_av, axis=0), np.std(diff_av, axis=0)/np.sqrt(nruns)


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
    #import person as Person
    import random
    import matplotlib
    import matplotlib.pyplot as plt
    import itertools
    I_0 = 100
    mode = "Probabilistic"
    N = 3000
    nruns = 1
    times = np.arange(100)

    cols = [["steelblue", "royalblue", "navy"], ["salmon", "red", "darkred"]]
    

    def calculate(mode):
        if mode=='Probabilistic':
            betas_sim = [0.050/N, 0.100/N, 0.150/N]
            betas_anal = [0.05, 0.1,0.150]
            simuls_av, simul,  anals, diff_av, diff = multi_run(I_0, N, times, betas_sim, betas_anal, nruns)
        else:
            betas_sim = [0.050, 0.100, 0.150]
            betas_anal = [0.050, 0.100, 0.150]
            simuls_av, simul,  anals, diff_av, diff = multi_run(I_0, N, times, betas_sim, betas_anal, nruns)

        return simuls_av, simul, anals, diff_av, diff

    modes = ['Probabilistic', 'Superposition']
    betas_anal = [0.05, 0.1,0.150]
    fig, axes = plt.subplots(2, 1, sharex=True)
    for j, mode in enumerate(modes):
        simuls_av, simul, anals, diff_av, diff = calculate(mode)
        for i in range(len(betas_anal)):
            beta = betas_anal[i]
            name = "$\\beta = $" + str(beta)
            axes[0].plot(times, simuls_av[i], label=name, color=cols[j][i])
            axes[0].fill_between(times, simuls_av[i]+simul[i], simuls_av[i]-simul[i], alpha =0.4, color = cols[j][i])
            axes[0].plot(times, anals[i], color=cols[j][i], linestyle="dashed")
            axes[1].plot(times, diff_av[i], color=cols[j][i])
            axes[1].fill_between(times, diff_av[i]+diff[i], diff_av[i]-diff[i], alpha =0.4, color = cols[j][i])
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


