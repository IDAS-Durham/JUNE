import group

#################################################################################
#################################################################################
#################################################################################

#################################################################################
#################################################################################
#################################################################################

def MakeInfection(starttime):
    tparams = {"Transmission:MeanProb": 0.6,
              "Transmission:Exponent": 2.,
              "Transmission:Norm":     4.}
    sparams = {"Symptoms:MaxSeverity": 0.5,
              "Symptoms:Tmean":       8.,
              "Symptoms:SigmaT":      4.}
    infect = infection.Infection(starttime)
    trans  = transmission.TransmissionXNExp(tparams,starttime)
    infect.SetTransmission(trans)
    sever  = symptoms.SymptomsGaussian(sparams,starttime)
    infect.SetSymptoms(sever)
    return infect

def Patient0(time):
    patient0 = person.Person("patient0")
    patient0.SetAge(50.)
    patient0.SetGender('M')
    patient0.SetInfection(MakeInfection(time))
    return patient0

def HealthCheck():
    test = group.Group("test", "group", 99, "Test")
    test.Add(Patient0(0))
    test.Output(True,False)

def SimpleChecks():
    testg = group.Group("testgroup","household")
    test1 = person.Person("test1")
    test2 = person.Person("test2")
    testg.Add(test1)
    testg.Add(test2)
    testg.Output()
    test3 = person.Person("test3")
    testg.Add(test3)
    testg.Output(True)
    testg.Add(test1)
    testg.Add(Patient0(0))
    testg.Output()    
    testg.Add(5)


if __name__=="__main__":
    import person
    import random
    import symptoms
    import transmission
    import infection
    #SimpleChecks()
    HealthCheck()
