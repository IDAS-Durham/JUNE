import numpy as np
import random
import transmission
import symptoms
import sys

class InfectionSelector:
    def __init__(self,Tparams,Sparams):
        self.Tparams = Tparams
        self.Sparams = Sparams

    def MakeInfection(self,time):
        trans = self.SelectTransmission(time)
        sever = self.SelectSeverity(time)
        infect = Infection(time)
        infect.SetTransmission(trans)
        infect.SetSymptoms(sever)
        return infect
        
    def SelectTransmission(self,time):
        if self.Tparams["Transmission:Type"]=="XNExp":
            names = ["Transmission:MeanProb",
                     "Transmission:Exponent",
                      "Transmission:Norm"]
            params, variations = self.MakeParams(self.Tparams,names)
            trans = transmission.TransmissionXNExp(params,time)
        elif self.Tparams["Transmission:Type"]=="Box":
            names = ["Transmission:MeanProb",
                     "Transmission:EndTime"]
            params, variations = self.MakeParams(self.Tparams,names)
            trans = transmission.TransmissionConstantInterval(params,time)
        trans.SetInterval(variations)
        trans.SetParameters()
        return trans

    def SelectSeverity(self,time):
        if self.Sparams["Symptoms:Type"]=="Gauss":
            names = ["Symptoms:MaxSeverity",
                     "Symptoms:Tmean",
                     "Symptoms:SigmaT"]
            params, variations = self.MakeParams(self.Sparams,names)
            sever = symptoms.SymptomsGaussian(params,time)
        sever.SetInterval(variations)
        sever.SetParameters()
        return sever
            
    def MakeParams(self,parameters,names):
        params     = {}
        variations = {}
        for name in names:
            params[name] = parameters[name]
            for key in ["Upper","Lower"]:
                variations[name+key] = parameters[name+key]
        print (params)
        print (variations)
        return params,variations
            
class Infection:
    """
    The description of the infection, with two time dependent characteristics,
    which may vary by individual:
    - transmission probability, Ptransmission.
    - symptom severity, Severity
    Either of them will be a numer between 0 (low) and 1 (high, strong sypmotoms), 
    and for both we will have some thresholds.
    Another important part for the infection is their begin, starttime, which must
    be given in the constructor.  Transmission probability and symptom severity
    can be added/modified a posteriori.
    """
    def __init__(self,time,trans=False,symp=False):
        self.Tthreshold = 0.01
        self.Sthreshold = 0.01
        self.starttime  = time
        self.trans      = trans
        self.symp       = symp

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
