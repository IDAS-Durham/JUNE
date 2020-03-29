import numpy as np
import random
import transmission
import symptoms
import sys

class Infection:
    def __init__(self,time):
        self.Tthreshold = 0.01
        self.Sthreshold = 0.01
        self.starttime  = time
        self.trans      = False
        self.symp       = False

    def SetTransmission(self, t):
        if not isinstance(t, transmission.Transmission):
            print ("Error in Infection.SetTransmission(",t,") is not a transmission.")
            print("--> Exit the code.")
            sys.exit()
        self.trans = t

    def GetTransmission(self):
        return self.trans
        
    def SetSymptoms(self, s):
        if not isinstance(s, symptoms.Symptoms):
            print ("Error in Infection.SetSymptoms(",s,") is not a symptoms.")
            print("--> Exit the code.")
            sys.exit()
        self.symp = s

    def GetSymptoms(self):
        return self.symp
        
    def Ptransmission(self,time):
        if not self.trans:
            return 0.
        return self.trans.Probability(time)

    def Severity(self,time):
        if not self.symp:
            return 0.
        return self.symp.Severity(time)
