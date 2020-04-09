import sys

sys.path.append("../covid")
from covid.transmission import Transmission
from covid.groups.people import Person
from covid.infection import Infection
from covid.infection_selector import InfectionSelector


def trivial_check():
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mean"] = 0.5
    selector = InfectionSelector(Tparams, None)
    infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
    print("Tparams = ", Tparams)
    print("   * Prob = ", infection.transmission_probability(1))

def distribute_value_Gamma():
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    person = Person('test',0,10,'M',0,0)
    
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]  = "Gamma"
    params["Mean"]  = 1.0
    params["Shape"] = 0.25
    selector = InfectionSelector(Tparams, None)
    probs1 = []
    for i in range(1000000):
        infection = selector.make_infection(person,0)
        probs1.append(infection.transmission_probability(1))

    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]  = "Gamma"
    params["Mean"]  = 1.0
    params["Shape"] = 0.5
    probs2 = []
    selector = InfectionSelector(Tparams, None)
    for i in range(1000000):
        infection = selector.make_infection(person,0)
        probs2.append(infection.transmission_probability(1))

    fig, axes = plt.subplots()
    axes.hist(
        probs1,
        1000,
        range=(0, 1),
        density=True,
        facecolor="blue",
        alpha=0.5,
        label="$\\Gamma(\\alpha = 0.25$, mean = 1.)",
    )
    axes.hist(
        probs2,
        1000,
        range=(0, 1),
        density=True,
        facecolor="red",
        alpha=0.5,
        label="$\\Gamma(\\alpha = 0.50$, mean = 1.)",
    )
    plt.yscale('log')
    axes.set_ylim([0.001,100.0])
    axes.legend()
    plt.show()

        
def distribute_value_Gauss():
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()

    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]      = "Gauss"
    params["Mean"]      = 0.5
    params["WidthPlus"] = 0.3
    params["Lower"]     = 0.0
    params["Upper"]     = 1.0

    selector = InfectionSelector(Tparams, None)
    probs1 = []
    for i in range(1000000):
        infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
        probs1.append(infection.transmission_probability(1))

    probs2 = []
    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]       = "Gauss"
    params["Mean"]       = 0.5
    params["WidthPlus"]  = 0.2
    params["WidthMinus"] = 0.1
    params["Lower"]      = 0.0
    params["Upper"]      = 1.0
    selector = InfectionSelector(Tparams, None)
    for i in range(1000000):
        infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
        probs2.append(infection.transmission_probability(1))

    axes.hist(
        probs1,
        1000,
        range=(0, 1),
        density=True,
        facecolor="blue",
        alpha=0.5,
        label="symmetric, width = 0.3",
    )
    axes.hist(
        probs2,
        1000,
        range=(0, 1),
        density=True,
        facecolor="red",
        alpha=0.5,
        label="symmetric, widths = 0.1, 0.2",
    )
    axes.legend()
    plt.show()

def check_symptom_tags(N):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    Tparams = {}
    Tparams["Transmission:Type"] = "SI"
    params = {}
    Tparams["Transmission:Probability"] = params
    params["Mode"]       = "Gauss"
    params["Mean"]       = 0.5
    Sparams = {}
    Sparams["Symptoms:Type"] = "Constant"
    MSparams = {}
    MSparams["Mean"]  = 0.5
    MSparams["Mode"]  = "Flat"
    MSparams["Lower"] = 0
    MSparams["Upper"] = 1
    Sparams["Symptoms:Severity"]   = MSparams
    TOparams = {}
    TOparams["Mean"] = 0.5
    Sparams["Symptoms:TimeOffset"] = TOparams
    MTparams = {}
    MTparams["Mean"] = 12
    Sparams["Symptoms:EndTime"]    = MTparams
    selector = InfectionSelector(Tparams, Sparams)

    health_index = [0.4, 0.55, 0.65, 0.8, 0.95]
    severs1  = []
    tags     = [0,   0,    0,    0,    0,    0]
    expected = [0.4, 0.15, 0.10, 0.15, 0.15, 0.05]
    allowed  = ["none","influenza-like illness", "pneumonia",
                "hospitalised", "intensive care",
                "dead"]
    for i in range(N):
        person    = Person('test',0,10,'M',health_index,0)
        infection = selector.make_infection(person,0)
        person.set_infection(infection)
        severs1.append(infection.symptom_severity(1))
        tag = person.get_symptoms_tag(1)
        for j in range(0,len(allowed)):
            if tag==allowed[j]:
                tags[j] += 1
                break
    for i in range(len(tags)):
        tags[i] = tags[i]/N
    print (tags)
        
    fig, axes = plt.subplots(2,1)
    axes[0].hist(severs1,20,range=(0, 1),
        density=True,facecolor="blue",alpha=0.5,
        label="flat distribution of severity",
    )
    axes[0].legend(loc='lower left')
    axes[1].bar(allowed,tags,
                color="blue",alpha=0.5,
                label="severity tag distribution")
    axes[1].scatter(allowed,expected,
                    color="black",
                    label="expected severity tag distribution")
    plt.show()

        

if __name__ == "__main__":
    #trivial_check()
    #distribute_value_Gauss()
    #distribute_value_Gamma()
    check_symptom_tags(1000000)
