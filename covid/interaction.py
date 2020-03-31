import group  as grp
import person as per
import infection
import sys
import random

class Interaction:
    def __init__(self):
        self.group     = False
        self.intensityMean  = 1.
        self.intensityWidth = 0.

    def CombinedTransmission(self,time):
        probNo = 1.
        for p in self.group.Infected():
            probNo *= (1.-p.Ptransmission(time) * self.Intensity(time))
        return 1.-probNo

    def SocialMixing(self,time):
        if (self.group.NInfected() == 0 or self.group.NHealthy() == 0): 
            return
        Ptrans = self.CombinedTransmission(time)
        for person in self.group.Healthy():
            print ("Testing ",person.Name())
            if random.random() < Ptrans:
                print (*"Person ",person.Name()," is now infected.")
        self.group.UpdateLists(time)

    def SetIntensity(self,mean,width=0.):
        self.intensityMean  = min(1.,max(0.,mean))
        self.intensityWidth = min(1.,max(0.,width))
        
    def Intensity(self,time):
        print (self.intensityMean,self.intensityWidth)
        if self.intensityWidth <1.e-3:
            return self.intensityMean
        intensity = -1.
        while intensity < 0. or intensity>1.:
            intensity = (random.gauss(self.intensityMean,self.intensityWidth) *
                         self.TimeProfile(time))
        return intensity

    def TimeProfile(self,time):
        return 1.

    def SetGroup(self,group):
        self.group = group
    
    def Group(self):
        return self.group
        

