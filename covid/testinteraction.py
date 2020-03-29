import interaction


class Tester:
    def __init__(self,groupsize=100,timesteps=1,deltaT=1):
        self.time        = 0
        self.groupsize   = groupsize
        self.timesteps   = timesteps
        self.deltaT      = deltaT
        self.tparams     = {"Transmission:MeanProb": 0.6,
                            "Transmission:Exponent": 2.,
                            "Transmission:Norm":     4.}
        self.sparams     = {"Symptoms:MaxSeverity": 0.5,
                            "Symptoms:Tmean":       8.,
                            "Symptoms:SigmaT":      4.}
        self.interaction = interaction.Interaction()
        self.InitTest(self.groupsize)
    
    def MakeInfection(self,starttime):
        infect = infection.Infection(starttime)
        trans  = transmission.TransmissionXNExp(self.tparams,starttime)
        infect.SetTransmission(trans)
        sever  = symptoms.SymptomsGaussian(self.sparams,starttime)
        infect.SetSymptoms(sever)
        return infect
    
    def Patient0(self,time):
        patient0 = person.Person("patient0")
        patient0.SetAge(50.)
        patient0.SetGender('M')
        patient0.SetInfection(self.MakeInfection(time))
        return patient0
    
    def TimeStep(self,time):
        print("======== timestep, ",time," ==========")
        self.interaction.Group().UpdateLists(time)
        self.interaction.SocialMixing(time)
        self.interaction.Group().Output()
        
        
    def InitTest(self,size):
        testgroup = group.Group("test", "group", size-1, "Test") 
        testgroup.Add(self.Patient0(0))
        testgroup.Output()
        self.interaction.SetGroup(testgroup)
        
if __name__=="__main__":
    import group
    import person
    import infection
    import transmission
    import symptoms
    import random
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt 

    testinter = interaction.Interaction()
    testinter.SetIntensity(0.8,0.05)
    time = np.arange(10000)
    ints = []
    for t in time:
        ints.append(testinter.Intensity(t))

    fig,axis = plt.subplots()
    axis.hist(ints,100,color='xkcd:sky blue',alpha=0.5)
    plt.show()
    
    tester  = Tester(100)
    time    = 0
    endtime = 1
    deltaT  = 1
    
    while time <= endtime:
        time += deltaT
        tester.TimeStep(time)
