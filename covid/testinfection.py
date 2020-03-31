import infection
import transmission
import symptoms
import numpy as np
import random


if __name__=="__main__":
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt 
    Tparams  = {"Transmission:Type":          "XNExp",
                "Transmission:MeanProb":      0.6,
                "Transmission:MeanProbUpper": 0.2,
                "Transmission:MeanProbLower": 0.1,
                "Transmission:Exponent":      2.,
                "Transmission:ExponentLower": 1.,
                "Transmission:ExponentUpper": 1.,
                "Transmission:Norm":          2.,
                "Transmission:NormUpper":     0.5,
                "Transmission:NormLower":     0.5}
    Sparams  = {"Symptoms:Type":              "Gauss",
                "Symptoms:MaxSeverity":       0.5,
                "Symptoms:MaxSeverityUpper":  0.15,
                "Symptoms:MaxSeverityLower":  0.15,
                "Symptoms:Tmean":             8.,
                "Symptoms:TmeanUpper":        2.,
                "Symptoms:TmeanLower":        2.,
                "Symptoms:SigmaT":            4.,
                "Symptoms:SigmaTUpper":       1.,
                "Symptoms:SigmaTLower":       1.}
    selector = infection.InfectionSelector(Tparams,Sparams)
    selector.MakeInfection(0)

    time = np.arange(0.0,20.0,0.01)
    fig,axes = plt.subplots(2,1,sharex='col')
    for i in range (0,100):
        infect = selector.MakeInfection(0)
        probs  = []
        severs = []
        for t in time:
            probs.append(infect.Ptransmission(t))
            severs.append(infect.Severity(t))
        axes[0].plot(time,probs,color='xkcd:sky blue',alpha=0.25)
        axes[1].plot(time,severs,color='xkcd:salmon',alpha=0.25)
    infect = selector.MakeInfection(0)
    probs  = []
    severs = []
    for t in time:
        probs.append(infect.Ptransmission(t))
        severs.append(infect.Severity(t))
    axes[0].plot(time,probs,color='blue',label = "T variations",linewidth=2)
    axes[1].plot(time,severs,color='red',label = "S variations",linewidth=2)
    axes[0].set_ylabel("$P_{trans}$")
    axes[1].set_ylabel("$Severity$")
    axes[0].legend()
    axes[1].legend()
    axes[1].set_xlabel("time")
    plt.show()
