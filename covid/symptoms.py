import numpy as np
import random


class Symptoms:
    """
    The probability for the individual symptom severity.
    This is time-dependent, and the actual value is calculated in the method
    Probability.  We allow to vary parameters around their mean value with
    a left- and right-sided Gaussian described by sigma and the result
    limited by 2 sigma in either direction or physical limits.  

    Currently one form is implemented:
    - SymptomsGaussian(Symptoms)
    S(t) = S_0 exp{-[t-(tstart+tmean)]^2/sigma^2} with parameters
    Symptoms:MaxSeverity, Symptoms:Tmean, and Symptoms:SigmaT, and with 
    variations set by combining the parameter name with the tags Lower and 
    Upper.

    TODO: we should try and map this onto the Flute/Imperial models, as far
    as possible, to have a baseline and to facilitate validation.
    """
    def __init__(self,params={},time=-1.):
        self.starttime = time
        self.severity      = 0.
        self.Init(params)

    def SetInterval(self,interval):
        pass

    def ResetParameters(self):
        pass
    
    def SetParameter(self,param,limits):
        delta    = -1.
        paramnew = -1.
        while delta < 0. or delta>2. or paramnew > limits[1] or paramnew < limits[0]:
            delta = random.gauss(0.,1.)
            if random.random() < param[1]/(param[1]+param[2]):
                paramnew = param[0] + delta * param[1]
            else:
                paramnew = param[0] - delta * param[2]
        return paramnew
            
    def Init(self,params):
        pass
    
    def Severity(self,time):
        if time > self.starttime:
            self.Calculate(time)
        else:
            self.severity = 0.
        return max(0.,self.severity)
        
        
    def Calculate(self,time):
        pass


#################################################################################
#################################################################################
#################################################################################
    
class NoSymptoms(Symptoms):
    pass

#################################################################################
#################################################################################
#################################################################################

class SymptomsGaussian(Symptoms):
    def Init(self,params):
        self.maxseverities = []
        self.Tmeans        = []
        self.sigmaTs       = []
        self.maxseverities.append(params["Symptoms:MaxSeverity"])
        self.Tmeans.append(params["Symptoms:Tmean"])
        self.sigmaTs.append(params["Symptoms:SigmaT"])
        self.ResetParameters()

    def ResetParameters(self):
        self.maxseverity = self.maxseverities[0]
        self.Tmean       = self.Tmeans[0]
        self.sigmaT      = self.sigmaTs[0]
        
    def SetInterval(self,params):
        self.maxseverities.append(params["Symptoms:MaxSeverityUpper"])
        self.maxseverities.append(params["Symptoms:MaxSeverityLower"])
        self.Tmeans.append(params["Symptoms:TmeanUpper"])
        self.Tmeans.append(params["Symptoms:TmeanLower"])
        self.sigmaTs.append(params["Symptoms:SigmaTUpper"])
        self.sigmaTs.append(params["Symptoms:SigmaTLower"])

    def SetParameters(self):
        limits = [0,1]
        self.maxseverity = Symptoms.SetParameter(self,self.maxseverities,limits)
        limits = [0,2*self.Tmeans[0]]
        self.Tmean = Symptoms.SetParameter(self,self.Tmeans,limits)
        limits = [0,2*self.sigmaTs[0]]
        self.sigmaT = Symptoms.SetParameter(self,self.sigmaTs,limits)
        
    def Calculate(self,time):
        dt = time - (self.starttime + self.Tmean)
        self.severity = (self.maxseverity * np.exp(-dt**2/self.sigmaT**2))
            

