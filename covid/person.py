import sys
import infection
import random

class Person:
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

    
