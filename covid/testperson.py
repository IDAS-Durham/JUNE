import person

#################################################################################
#################################################################################
#################################################################################

#################################################################################
#################################################################################
#################################################################################


def SimpleChecks():
    print ("Exception handling for Person:")
    testperson = person.Person("test")
    testperson.Output()
    testperson.SetAge(5.)
    testperson.Output()
    testperson.SetGender('M')
    testperson.Output()
    testperson = person.Person(0, "Test")
    testperson.Output()
    print(type(testperson))


def TestInfection():
    testperson = person.Person("test",True)
    testperson.SetAge(50.)
    testperson.SetGender('M')

    starttime = 2
    infect = infection.Infection(starttime)
    params = {"Transmission:MeanProb": 0.6,
              "Transmission:Exponent": 2.,
              "Transmission:Norm":     4.}
    trans  = transmission.TransmissionXNExp(params,starttime)
    infect.SetTransmission(trans)
    params = {"Symptoms:MaxSeverity": 0.5,
              "Symptoms:Tmean":       8.,
              "Symptoms:SigmaT":      4.}
    sever  = symptoms.SymptomsGaussian(params,starttime)
    infect.SetSymptoms(sever)
    testperson.SetInfection(infect)
    
    time   = np.arange(0.0,20.0,0.02)
    probs  = []
    severs = []
    for t in time:
        probs.append(testperson.Ptransmission(t))
        severs.append(testperson.Symptoms(t))

    fig,ax = plt.subplots()
    ax.plot(time,probs,color="xkcd:blue",linestyle="-",label="Transmission")
    ax.plot(time,severs,color="xkcd:red",linestyle="-",label="Symptoms")
    ax.legend()
    ax.set_title("Infection test for Person")
    ax.set_xlabel("time")
    ax.set_ylabel("probability/severity")
    plt.show()


if __name__=='__main__':
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt 
    import transmission
    import symptoms
    import infection
    SimpleChecks()
    TestInfection()
