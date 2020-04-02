import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

sys.path.append("../covid")
import group       as Group
import interaction as Interaction
import infection   as Infection

def ratio_infecteds(beta,times):
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params 
    params["Mean"] = beta
    selector  = Infection.InfectionSelector(Tparams,None)
    group     = Group.Group("test", "Random", 1000)
    group.set_intensity(group.get_intensity()/group.size())
    group.people[0].set_infection(selector.make_infection(0))
    groups = []
    groups.append(group)
    interaction = Interaction.Interaction(groups,0)
    ratio = []
    for time in times:
        ratio.append(group.size_infected()/group.size())
        interaction.single_time_step(time,selector)
        group.update_status_lists()
    return ratio

if __name__=="__main__":
    import person as Person
    import random
    import matplotlib
    import matplotlib.pyplot as plt
    
    betas  = [0.10,0.15,0.20]
    ratios = []
    times  = np.arange(100)
    for beta in betas:
        ratios.append(ratio_infecteds(beta,times))
        
    fig, axes = plt.subplots()
    for i in range(len(betas)):
        beta  = betas[i]
        ratio = ratios[i]
        name  = "$\\beta = $"+str(beta)
        plt.plot(times,ratio,label=name)
        print (name)
    plt.legend()
    plt.show()
