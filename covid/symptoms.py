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
    def __init__(self,params,time):
        self.starttime = time
        self.severity  = 0.
        self.Init(params)

    def SetInterval(self,interval):
        pass

    def ResetParameters(self):
        pass
            
    def Init(self,params):
        pass
    
    def Severity(self,time):
        if time >= self.starttime:
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
        self.maxseverity = min(1., max(0., params["Symptoms:MaximalSeverity"]["Value"]))
        self.Tmean = max(0., params["Symptoms:MeanTime"]["Value"])
        self.sigmaT = max(0.001, params["Symptoms:SigmaTime"]["Value"])
        
    def Calculate(self,time):
        dt = time - (self.starttime + self.Tmean)
        self.severity = (self.maxseverity * np.exp(-dt**2/self.sigmaT**2))
            