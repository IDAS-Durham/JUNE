import sys
import infection
import random



class Person:
    """
    Primitive version of class person.  This needs to be connected to the full class 
    structure including health and social indices, employment, etc..  The current 
    implementation is only meant to get a simplistic dynamics of social interactions coded.
    
    The logic is the following:
    People can get infected with an Infection, which is characterised by time-dependent
    transmission probabilities and symptom severities (see class descriptions for
    Infection, Transmission, Severity).  The former define the infector part for virus
    transmission, while the latter decide if individuals realise symptoms (we need
    to define a threshold for that).  The symptoms will eventually change the behavior 
    of the person (i.e. intensity and frequency of social contacts), if they need to be 
    treated, hospitalized, plugged into an ICU or even die.  This part of the model is 
    still opaque.   
    
    Since the realization of the infection will be different from person to person, it is
    a characteristic of the person - we will need to allow different parameters describing
    the same functional forms of transmission probability and symptom severity, distributed
    according to a (tunable) parameter distribution.  Currently a non-symmetric Gaussian 
    smearing of 2 sigma around a mean with left-/right-widths is implemented.
    
    TODO for person.py: 
    -- add age/gender/etc distribution according to census when instantiating a person.  
    This means we need to merge different parts of the code.
    """
    def __init__(self, name, mode="None"):
        self.pname = name
        self.InitDefaults()
        if mode == "Test":
            self.SetAge(random.randrange(0.,100.))
            self.SetGender(random.choice(("M", "F")))

    def InitDefaults(self):
        self.age     = -1;
        self.gender  = 'U'
        self.healthy = True

    def Output(self,time=0):
        print ("--------------------------------------------------")
        print ("Person [",self.pname,"]: age = ",self.age," gender = ",self.gender)
        if self.IsInfected(0):
            print ("-- person is infected, transmission probability = ",
                   self.infect.Ptransmission(time))
        else:
            print ("-- person is healthy.")

    def SetInfection(self,i):
        if not isinstance(i, infection.Infection) and not i==False:
            print ("Error in Infection.Add(",i,") is not an infection")
            print("--> Exit the code.")
            sys.exit()
        self.infect  = i
        if not self.infect == False:
            self.healthy = False

    def SetAge(self,age=-1):
        if self.age > 0. or age < 0:
            print ("Error in Person.SetAge(",self.age," --> ",age,".")
            print ("--> Will end the run.")
            sys.exit(1)
        else:
            self.age = age
         

    def SetGender(self,gender):
        if self.gender != 'U' or not (gender == "M" or gender == "F"):
            print ("Error in Person.SetGender(",self.gender," --> ",gender,".")
            sys.exit(1)
        else:
            self.gender = gender

    def IsInfected(self,time):
        return not self.IsHealthy(time)

    def IsHealthy(self,time):
        return self.healthy

    def Ptransmission(self,time):
        return self.infect.Ptransmission(time)

    def Symptoms(self,time):
        return self.infect.Severity(time)

    def Age(self):
        return self.age

    def Gender(self):
        return self.gender

    def Name(self):
        return self.pname

    
