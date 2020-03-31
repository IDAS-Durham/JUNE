import symptoms

#################################################################################
#################################################################################
#################################################################################
#################################################################################
#################################################################################



#################################################################################
#################################################################################
#################################################################################
#################################################################################
#################################################################################

def ShowDistributions():
    time   = np.arange(0.0,20.0,0.02)
    severs = []
    forms  = []
    labels = []
    colors = []
    styles = []
    params = {"Symptoms:MaxSeverity": 0.5,
              "Symptoms:Tmean":       8.,
              "Symptoms:SigmaT":      4.}
    forms.append(symptoms.SymptomsGaussian(params, 0.))
    labels.append("0.5 * exp(-(Delta t-8)^2/4^2)")
    colors.append("xkcd:black")
    styles.append("-")
    params = {"Symptoms:MaxSeverity": 1.,
              "Symptoms:Tmean":       8.,
              "Symptoms:SigmaT":      8.}
    forms.append(symptoms.SymptomsGaussian(params,0.))
    labels.append("0.5 * exp(-(Delta t-8)^2/8^2)")
    colors.append("xkcd:black")
    styles.append(":")
                       
    for i in range(0,len(forms)):
        severs.append([])
    for t in time:
        for i in range(0,len(forms)):
            s = forms[i].Severity(t)
            severs[i].append(s)
                       
    fig,ax = plt.subplots()
    for i in range(0,len(forms)):
        ax.plot(time,severs[i],label=labels[i],color=colors[i],linestyle=styles[i])
    ax.legend()
    ax.set_title("Symptoms severities: Forms")
    ax.set_xlabel("time")
    ax.set_ylabel("probability (normed)")
    plt.show()
                       
def MakeSmearedPlots():
    time = np.arange(0.0,20.0,0.01)
    params = {"Symptoms:MaxSeverity": 0.5,
              "Symptoms:Tmean":       8.,
              "Symptoms:SigmaT":      4.}
    symp = symptoms.SymptomsGaussian(params,0.)
    symp.SetInterval({"Symptoms:MaxSeverityLower": 0.25,
                          "Symptoms:MaxSeverityUpper": 0.10,
                          "Symptoms:TmeanLower":       1.,
                          "Symptoms:TmeanUpper":       1.,
                          "Symptoms:SigmaTLower":      1.,
                          "Symptoms:SigmaTUpper":      1.})
    fig,ax = plt.subplots()
    for i in range (0,100):
        symp.SetParameters()
        res = []
        for t in time:
            res.append(symp.Severity(t))
        ax.plot(time,res,color='xkcd:sky blue',alpha=0.5)
    symp.ResetParameters()
    ax.plot(time,res,label = "0.8 x exp(-x) + variations",color='blue')
    ax.legend()
    ax.set_title("Symptoms probabilities: Variations")
    ax.set_xlabel("time")
    ax.set_ylabel("probability (normed)")
    plt.show()

if __name__=="__main__":
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt 
    print ("Self testing symptoms")
    ShowDistributions()
    MakeSmearedPlots()

