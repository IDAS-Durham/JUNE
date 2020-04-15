import sys

sys.path.append("../covid")
from covid.transmission import Transmission
from covid.groups.people import Person
from covid.infection import Infection
from covid.infection_selector import InfectionSelector


def trivial_check(config):
    selector = InfectionSelector(config)
    infection = selector.make_infection(Person('test',0,10,'M',0,0),0)
    print("transmission parameters = ", config["infection"]["transmission"])
    print("   * Prob = ", infection.transmission_probability(1))

def distribute_value_Gamma(config1,config2):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    person = Person('test',0,10,'M',0,0)
    
    selector1 = InfectionSelector(config1)
    probs1 = []
    for i in range(1000000):
        infection = selector1.make_infection(person,0)
        probs1.append(infection.transmission_probability(1))

    selector2 = InfectionSelector(config2)
    probs2 = []
    for i in range(1000000):
        infection = selector2.make_infection(person,0)
        probs2.append(infection.transmission_probability(1))

    fig, axes = plt.subplots()
    axes.hist(probs1,1000,range=(0, 1),density=True,
              facecolor="blue",alpha=0.5,
              label="$\\Gamma(\\alpha = 0.25$, mean = 1.)")
    axes.hist(probs2,1000,range=(0, 1),density=True,
              facecolor="red",alpha=0.5,
              label="$\\Gamma(\\alpha = 0.50$, mean = 1.)",
    )
    plt.yscale('log')
    axes.set_ylim([0.001,100.0])
    axes.legend()
    plt.show()

        
def distribute_value_Gauss(config1,config2):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots()

    selector1 = InfectionSelector(config1)
    probs1 = []
    for i in range(1000000):
        infection = selector1.make_infection(Person('test',0,10,'M',0,0),0)
        probs1.append(infection.transmission_probability(1))

    probs2 = []
    selector2 = InfectionSelector(config2)
    for i in range(1000000):
        infection = selector2.make_infection(Person('test',0,10,'M',0,0),0)
        probs2.append(infection.transmission_probability(1))

    axes.hist(probs1,1000,range=(0, 1),density=True,
              facecolor="blue",alpha=0.5,
              label="symmetric, width = 0.3",
    )
    axes.hist(probs2,1000,range=(0, 1),density=True,
              facecolor="red",alpha=0.5,
              label="symmetric, widths = 0.1, 0.2")
    axes.legend()
    plt.show()

def check_symptom_tags(N,config):
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    selector = InfectionSelector(config)

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
    import os
    import yaml
    
    config_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        "tests",
        "config_infection_test.yaml",
    )
    with open(config_file, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    found = False

    if "trivial_check" in config:
        print ("trivial check")
        trivial_check(config["trivial_check"])
        found = True        
    if ("distribute_value_Gamma1" in config and
        "distribute_value_Gamma2" in config):
        print ("gamma distribution")
        distribute_value_Gamma(config["distribute_value_Gamma1"],
                               config["distribute_value_Gamma2"])
        found = True        
    if ("distribute_value_Gauss1" in config and
        "distribute_value_Gauss2" in config):
        print ("gauss distribution")
        distribute_value_Gauss(config["distribute_value_Gauss1"],
                               config["distribute_value_Gauss2"])
        found = True
    if "symptoms_tag_test" in config:
        print ("symptoms_tag_test")
        check_symptom_tags(1000000,config["symptoms_tag_test"])
        found = True
    if not found:
        print ("no keywords found:",config)
