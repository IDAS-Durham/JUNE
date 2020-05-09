import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from june.groups.test_groups.test_group import TestGroups
from june.interaction import Interaction
from june.collective_interaction import CollectiveInteraction
from june.infection import Infection


def ratio_SI_simulated(beta, N, I_0, times, mode):
    config = {}
    config["interaction"] = {}
    config["interaction"]["type"] = "collective"
    config["interaction"]["mode"] = mode
    config["interaction"]["parameters"] = {}
    config["infection"] = {}
    config["infection"]["transmission"] = {}
    config["infection"]["transmission"]["type"] = "SI"
    config["infection"]["transmission"]["probability"] = {}
    config["infection"]["transmission"]["probability"]["mean"] = beta
    selector = InfectionSelector(Tparams, None)
    groups = TestGroups(people_per_group=N, total_people=N)
    group = groups.members[0]
    if mode == "superposition":
        group.set_intensity_of_group_type(group.get_intensity_from_group_type())
    for i in range(I_0):
        group.people[i].set_infection(selector.make_infection(group.people[i], 0))
    interaction = CollectiveInteraction(selector, config)
    ratio = []
    print("===============================================")
    for time in times:
        value = group.size_infected() / group.size()
        if time / 10 == int(time / 10):
            print(time, value)
        ratio.append(value)
        interaction.set_time(time)
        interaction.set_groups([groups])
        interaction.time_step()
    return ratio


def ratio_SI_analytic(beta, N, I_0, times):
    print("-----------------------------------------------")
    ratios = []
    for time in times:
        ratio = I_0 / ((N - I_0) * np.exp(-beta * time) + I_0)
        if time / 10 == int(time / 10):
            print(time, ratio)
        ratios.append(ratio)
    return ratios


def ratio_SIR_simulated(beta, gamma, N, I_0, times, mode):
    config = {}
    config["interaction"] = {}
    config["interaction"]["type"] = "collective"
    config["interaction"]["probmode"] = mode
    config["interaction"]["parameters"] = {}
    config["infection"] = {}
    config["infection"]["transmission"] = {}
    config["infection"]["transmission"]["type"] = "SIR"
    config["infection"]["transmission"]["probability"] = {}
    config["infection"]["transmission"]["probability"]["mean"] = beta
    config["infection"]["transmission"]["recovery"] = {}
    config["infection"]["transmission"]["recovery"]["mean"] = gamma
    config["infection"]["transmission"]["recovery_cutoff"] = {}
    config["infection"]["transmission"]["recovery_cutoff"]["mean"] = 1000
    selector = InfectionSelector(config)
    groups = TestGroups(people_per_group=N, total_people=N)
    group = groups.members[0]
    if mode == "Superposition":
        group.set_intensity_of_group_type(group.get_intensity_from_group_type())
    for i in range(I_0):
        group.people[i].set_infection(
            selector.make_infection(group.people[i], times[0] - 1)
        )
    group.output()
    interaction = CollectiveInteraction(selector, config)
    interaction.set_groups([groups])
    ratio = []
    print("===============================================")
    ratioI_by_N = []
    ratioR_by_N = []
    for time in times:
        valueI = group.size_infected() / group.size()
        valueR = group.size_recovered() / group.size()
        if time / 10 == int(time / 10):
            print(time, valueI, valueR)
        ratioI_by_N.append(valueI)
        ratioR_by_N.append(valueR)
        interaction.set_time(time)
        interaction.set_groups([groups])
        interaction.time_step()
    return ratioI_by_N, ratioR_by_N


def ratio_SIR_numerical(beta, gamma, N, I_0, times):
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
    S = N - I_0
    R = 0
    step = 10
    for time in times:
        for i in range(step):
            S = S - beta / step * S * I / N
            I = I + beta / step * S * I / N - gamma / step * I
            R = R + gamma / step * I
        ratioI = I / N
        ratioR = R / N
        if time / 10 == int(time / 10):
            print(time, ratioI, ratioR)
        ratioI_by_N.append(ratioI)
        ratioR_by_N.append(ratioR)
    return ratioI_by_N, ratioR_by_N


def multi_run(I_0, N, times, betas_sim, betas_anal, nruns, mode):
    simul_av = np.zeros((nruns, len(betas_sim), len(times)))
    diff_av = np.zeros((nruns, len(betas_sim), len(times)))
    for i in range(nruns):
        simuls = []
        anals = []
        diffs = []
        for beta_sim, beta_anal in zip(betas_sim, betas_anal):
            simul = ratio_SI_simulated(beta_sim, N, I_0, times, mode)
            anal = ratio_SI_analytic(beta_anal, N, I_0, times)
            simuls.append(simul)
            anals.append(anal)
            diff = []
            for j in range(len(times)):
                diff.append(simul[j] / anal[j])
            diffs.append(diff)
        simul_av[i] = np.array(simuls)
        diff_av[i] = np.array(diffs)

    return (
        np.mean(simul_av, axis=0),
        np.std(simul_av, axis=0) / np.sqrt(nruns),
        anals,
        np.mean(diff_av, axis=0),
        np.std(diff_av, axis=0) / np.sqrt(nruns),
    )


def test_SI():
    I_0 = 10
    mode = "Probabilistic"
    N = 1000
    nruns = 10
    times = np.arange(0, 100)

    delta_ref = []
    for i in times:
        delta_ref.append(1)

    cols = [["steelblue", "royalblue", "navy"], ["salmon", "red", "darkred"]]

    def calculate(mode):
        if mode == "Probabilistic":
            betas_sim = [0.1]  # [0.050, 0.100, 0.150]
            betas_anal = [0.1]  # [0.050, 0.100, 0.150]
            simuls_av, simul, anals, diff_av, diff = multi_run(
                I_0, N, times, betas_sim, betas_anal, nruns, mode
            )
        else:
            betas_sim = [0.1]  # [0.050, 0.100, 0.150]
            betas_anal = [0.1]  # [0.050, 0.100, 0.150]
            simuls_av, simul, anals, diff_av, diff = multi_run(
                I_0, N, times, betas_sim, betas_anal, nruns, mode
            )

        return simuls_av, simul, anals, diff_av, diff

    modes = ["Probabilistic", "Superposition"]
    names = ["mult", "add"]
    betas_anal = [0.1]  # [0.050, 0.100,0.150]
    fig, axes = plt.subplots(2, 1, sharex=True)
    for j, mode in enumerate(modes):
        simuls_av, simul, anals, diff_av, diff = calculate(mode)
        for i in range(len(betas_anal)):
            beta = betas_anal[i]
            name = "$\\beta = $" + str(beta) + " (" + names[j] + ")"
            axes[0].plot(times, simuls_av[i], label=name, color=cols[j][i])
            axes[0].fill_between(
                times,
                simuls_av[i] + simul[i],
                simuls_av[i] - simul[i],
                alpha=0.4,
                color=cols[j][i],
            )
            axes[0].plot(times, anals[i], color=cols[j][i], linestyle="dashed")
            axes[1].plot(times, diff_av[i], color=cols[j][i])
            axes[1].fill_between(
                times,
                diff_av[i] + diff[i],
                diff_av[i] - diff[i],
                alpha=0.4,
                color=cols[j][i],
            )
            print(name)
    axes[0].legend()
    axes[0].set_ylabel("infected ratio")
    axes[0].set_yscale
    titlestring = (
        str(nruns)
        + " simulation runs ($N = "
        + str(N)
        + "$, $N_0 = "
        + str(I_0)
        + "$) vs SI model"
    )
    axes[0].set_title(titlestring)
    axes[1].plot(times, delta_ref, color="black", linestyle="dashed")
    axes[1].set_ylabel("simulation/analytic")
    axes[1].set_xlabel("time")
    fig.suptitle("Ratio of infected people (SI)")
    plt.show()


def test_SIR(config):
    N = 10000
    N0 = 50
    betas = [0.300]
    gammas = [0.100]
    colsR = ["salmon", "red", "darkred"]
    colsI = ["steelblue", "royalblue", "navy"]
    stylesnum = ["solid"]
    stylessim = ["dashed"]
    infNnum = []
    recNnum = []
    infNsim = []
    recNsim = []
    times = np.arange(0, 100)
    for i in range(len(betas)):
        beta = betas[i]
        gamma = gammas[i]
        print("beta = ", beta, ", gamma = ", gamma)
        infected, recovered = ratio_SIR_numerical(beta, gamma, N, N0, times)
        infNnum.append(infected)
        recNnum.append(recovered)
        print("N, N0 = ", N, N0)
        infected, recovered = ratio_SIR_simulated(
            beta, gamma, N, N0, times, "Probabilistic"
        )
        infNsim.append(infected)
        recNsim.append(recovered)

    fig, axis = plt.subplots(1, 1, sharex=True)
    for i in range(len(betas)):
        beta = betas[i]
        gamma = gammas[i]
        name = "$\\beta = $" + str(beta) + ", $\\gamma = $" + str(gamma)
        axis.plot(
            times,
            infNnum[i],
            label=name + ": infected",
            color=colsI[i],
            linestyle=stylesnum[i],
        )
        axis.plot(
            times,
            recNnum[i],
            label=name + ": recovered",
            color=colsR[i],
            linestyle=stylesnum[i],
        )
        axis.plot(
            times,
            infNsim[i],
            label=name + ": infected",
            color=colsI[i],
            linestyle=stylessim[i],
        )
        axis.plot(
            times,
            recNsim[i],
            label=name + ": recovered",
            color=colsR[i],
            linestyle=stylessim[i],
        )
        print(name)
    fig.suptitle("Ratios of infected and recovered people (SIR)")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    # import person as Person
    import random
    import matplotlib
    import matplotlib.pyplot as plt
    import itertools
    import os
    import yaml

    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "tests",
        "config_interaction_test.yaml",
    )
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    testmode = config["infection"]["testmode"]
    if testmode == "SIR":
        test_SIR(config)
    if testmode == "SI":
        test_SIR(config)
