import sys
sys.path.append("../covid")
import transmission as Transmission
import infection as Infection
import symptoms as Symptoms

def trivial_check():
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    tparams = {}
    Tparams["Transmission:Probability"] = tparams 
    tparams["Mean"] = 0.5

    Sparams = {}
    Sparams["Symptoms:Type"] = "Gauss"
    params_MS = {}
    params_MT = {}
    params_ST = {}
    Sparams["Symptoms:MaximalSeverity"] = params_MS
    Sparams["Symptoms:MeanTime"] = params_MT # incubation period
    Sparams["Symptoms:SigmaTime"] = params_ST # approx how long it takes to get better
    params_MS["Mean"] = 0.8
    params_MT["Mean"] = 7.0
    params_ST["Mean"] = 10.0
    selector  = Infection.InfectionSelector(Tparams, Sparams)
    infection = selector.make_infection(0)
    print ("Tparams = ", Tparams)
    print ("Sparams = ", Sparams)
    print ("   * Symptom severity = ", infection.symptom_severity(1))

def distribute_value():
    import random
    import matplotlib.pyplot as plt

    # fix transmission params to be constant
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params 
    params["Mean"] = 0.5

    Sparams = {}
    Sparams["Symptoms:Type"] = "Gauss"
    # dictionary for each parameters for now. probably better to have just one for all of them.
    params_MS = {}
    params_MT = {}
    params_ST = {}
    Sparams["Symptoms:MaximalSeverity"] = params_MS
    Sparams["Symptoms:MeanTime"] = params_MT
    Sparams["Symptoms:SigmaTime"] = params_ST
    params_MS["Mean"] = 0.8
    params_MS["WidthPlus"] = 0.2
    params_MS["WidthMinus"] = 0.2
    params_MT["Mean"] = 5.0
    params_MT["WidthPlus"] = 2.0
    params_MT["WidthMinus"] = 1.0
    params_ST["Mean"] = 7.0
    params_ST["WidthPlus"] = 3.0
    params_ST["WidthMinus"] = 2.0

    selector = Infection.InfectionSelector(Tparams, Sparams)
    severities1 = []
    severity_t = []
    for i in range(100000):
        infection = selector.make_infection(0)
        severities1.append(infection.symptom_severity(1))
        if i == 0:
            for t in range(20):
                severity_t.append(infection.symptom_severity(t))

    params_MS["Mean"] = 0.8
    params_MS["WidthPlus"] = 0.2
    params_MS["WidthMinus"] = 0.2
    params_MT["Mean"] = 10.0
    params_MT["WidthPlus"] = 2.0
    params_MT["WidthMinus"] = 1.0
    params_ST["Mean"] = 14.0
    params_ST["WidthPlus"] = 3.0
    params_ST["WidthMinus"] = 2.0

    severities2 = []
    for _ in range(100000):
        infection = selector.make_infection(0)
        severities2.append(infection.symptom_severity(1))

    fig, ax = plt.subplots(1, 2, figsize=(9, 4))
    ax[0].set_title('Two different parameter sets')
    ax[0].hist(severities1, bins=100, density=True, alpha=0.5, color='C0', label='Param set 1')
    ax[0].hist(severities2, bins=100,  density=True, alpha=0.5, color='C1', label='Param set 2')
    ax[1].set_title('Evolution of symptom severity over time')
    ax[1].plot(severity_t)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    trivial_check()
    distribute_value()