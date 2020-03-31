import transmission

#################################################################################
#################################################################################
#################################################################################
#################################################################################
#################################################################################

def ShowDistributions():
    time   = np.arange(0.0,20.0,0.01)
    probs  = []
    forms  = []
    labels = []
    colors = []
    styles = []
    params = {"Transmission:MeanProb": 0.5,
              "Transmission:EndTime":  8.}
    forms.append(transmission.TransmissionConstantInterval(params, 1.))
    labels.append("constant interval")
    colors.append("xkcd:black")
    styles.append("-")
    params = {"Transmission:MeanProb": 0.8,
              "Transmission:Exponent": 1.,
              "Transmission:Norm":     1.}
    forms.append(transmission.TransmissionXNExp(params,0.))
    labels.append("0.8 x exp(-x)")
    colors.append("xkcd:blue")
    styles.append("-")
    params = {"Transmission:MeanProb": 0.8,
              "Transmission:Exponent": 1.,
              "Transmission:Norm":     6.}
    forms.append(transmission.TransmissionXNExp(params,0.))
    labels.append("0.8 x exp(-x/6)")
    colors.append("xkcd:blue")
    styles.append("--")
    params = {"Transmission:MeanProb": 0.8,
              "Transmission:Exponent": 2.,
              "Transmission:Norm":     4}
    forms.append(transmission.TransmissionXNExp(params,0.))
    labels.append("0.8 x^2 exp(-x/4)")
    colors.append("xkcd:blue")
    styles.append(":")
                       
    for i in range(0,len(forms)):
        probs.append([])
    for t in time:
        for i in range(0,len(forms)):
            p = forms[i].Probability(t)
            probs[i].append(p)
                       
    fig,ax = plt.subplots()
    for i in range(0,len(forms)):
        ax.plot(time,probs[i],label=labels[i],color=colors[i],linestyle=styles[i])
    ax.legend()
    ax.set_title("Transmission probabilities: Forms")
    ax.set_xlabel("time")
    ax.set_ylabel("probability (normed)")
    plt.show()
                       
def CheckGaussiansForParameterSmearing():
    params = {"Transmission:MeanProb": 0.5,
              "Transmission:EndTime":  8.}
    trans = transmission.TransmissionConstantInterval(params, 1.)
    trans.SetInterval({"Transmission:MeanProbUpper": 0.2,
                       "Transmission:MeanProbLower": 0.05,
                       "Transmission:EndTimeUpper":  2.,
                       "Transmission:EndTimeLower":  3.})
    MPs = []
    ETs = []
    for i in range(100000):
        trans.SetParameters()
        mp = trans.MeanProb()
        et = trans.EndTime()
        MPs.append(mp)
        ETs.append(et)
    fig, axes = plt.subplots(1,2)
    nBins = 50
    axes[0].hist(MPs, nBins, density=True, facecolor='blue', alpha=0.5)
    axes[0].set_ylabel("N_probability")
    axes[0].set_title("$\mathcal{P} = 0.5 \stackrel{+0.2}{-0.05}$")
    axes[1].hist(ETs, nBins, density=True, facecolor='blue', alpha=0.5)
    axes[1].set_ylabel("N_interval")
    axes[1].set_title(r"$\mathcal{P} = 8 \stackrel{+2}{-3}$")
    plt.show()

def MakeSmearedPlots():
    time = np.arange(0.0,10.0,0.01)
    params = {"Transmission:MeanProb": 0.8,
              "Transmission:Exponent":2.,
              "Transmission:Norm":0.5}
    trans = transmission.TransmissionXNExp(params,0.)
    trans.SetInterval({"Transmission:MeanProbUpper": 0.02,
                       "Transmission:MeanProbLower": 0.02,
                       "Transmission:ExponentUpper": 0.25,
                       "Transmission:ExponentLower": 0.25,
                       "Transmission:NormUpper":     0.1,
                       "Transmission:NormLower":     0.1})
    fig,ax = plt.subplots()
    for i in range (0,100):
        trans.SetParameters()
        res = []
        for t in time:
            res.append(trans.Probability(t))
        ax.plot(time,res,color='xkcd:sky blue',alpha=0.5)
    trans.ResetParameters()
    ax.plot(time,res,label = "0.8 x exp(-x) + variations",color='blue')
    ax.legend()
    ax.set_title("Transmission probabilities: Variations")
    ax.set_xlabel("time")
    ax.set_ylabel("probability (normed)")
    plt.show()

if __name__=="__main__":
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt 
    print ("Self testing transmissions")
    ShowDistributions()
    CheckGaussiansForParameterSmearing()
    MakeSmearedPlots()

    
