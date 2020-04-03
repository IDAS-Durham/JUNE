import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

sys.path.append("../covid")
import group       as Group
import interaction as Interaction
import infection   as Infection

def ratio_SI_simulated(beta,N,times,mode):
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params 
    params["Mean"] = beta
    selector  = Infection.InfectionSelector(Tparams,None)
    group     = Group.Group("test", "Random", N)
    group.set_intensity(group.get_intensity()/group.size())
    group.people[0].set_infection(selector.make_infection(0))
    groups = []
    groups.append(group)
    interaction = Interaction.Interaction(groups,0,mode)
    ratio = []
    print ("===============================================")
    for time in times:
        value = group.size_infected()/group.size()
        if time/10==int(time/10):
            print (time,value)
        ratio.append(value)
        interaction.single_time_step(time,selector)
        group.update_status_lists()
    return ratio

def ratio_SI_analytic(beta,N,times):
    print ("-----------------------------------------------")
    ratios = []
    for time in times:
        ratio = 1./((N-1.)*np.exp(-beta*time) + 1.)
        if time/10==int(time/10):
            print (time,ratio)
        ratios.append(ratio)
    return ratios
        
if __name__=="__main__":
    import person as Person
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    mode   = "Probabilistic"
    N      = 1000
    betas  = [0.050,0.100,0.150]
    cols   = ["steelblue","royalblue","navy"]
    simuls = []
    anals  = []
    diffs  = []
    times  = np.arange(100)
    for beta in betas:
        simul = ratio_SI_simulated(beta,N,times,mode)
        anal  = ratio_SI_analytic(beta,N,times)
        simuls.append(ratio)
        anals.append(SI)
        diff = []
        for i in range(len(times)):
            diff.append(ratio[i]/SI[i])
        diffs.append(diff)
        
    fig, axes = plt.subplots(2,1,sharex=True)
    for i in range(len(betas)):
        beta  = betas[i]
        name  = "$\\beta = $"+str(beta)
        axes[0].semilogy(times,simuls[i],label=name,color=cols[i])
        axes[0].semilogy(times,anals[i],color=cols[i],linestyle="dashed")
        axes[1].plot(times,diffs[i],color=cols[i])
        print (name)
    axes[0].legend()
    axes[0].set_ylabel("infected ratio")
    axes[0].set_yscale
    titlestring = "N = "+str(N)+", simulation vs SI model"
    axes[0].set_title(titlestring)
    axes[1].set_ylabel("simulation/analytic")
    axes[1].set_xlabel("time")
    fig.suptitle("Ratio of infected people")
    plt.show()
