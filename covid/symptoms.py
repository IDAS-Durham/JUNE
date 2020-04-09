import numpy as np
import random

allowed_symptom_tags = ["none",
                        "influenza-like illness", "pneumonia",
                        "hospitalised", "intensive care",
                        "dead"]

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
    def __init__(self,person,params,time):
        self.tags      = allowed_symptom_tags
        self.person    = person
        self.starttime = time
        self.severity  = 0.
        self.init(params)
        
    def set_interval(self,interval):
        pass

    def reset_parameters(self):
        pass
            
    def init(self,params):
        pass
    
    def get_severity(self,time):
        if time >= self.starttime:
            self.calculate(time)
        else:
            self.severity = 0.
        return max(0.,self.severity)

    def n_tags(self):
        return len(self.tags)

    def tag(self,tagno):
        if tagno>=self.n_tags():
            return self.tags[self.n_tags()-1]
        return self.tags[tagno]

    def tags(self):
        return self.tags
        
    def calculate(self,time):
        pass


#################################################################################
#################################################################################
#################################################################################
    
class SymptomsConstant(Symptoms):
    def init(self,params):
        self.Toffset     = max(0., params["Symptoms:TimeOffset"]["Value"])
        self.Tend        = max(0., params["Symptoms:EndTime"]["Value"])
        self.maxseverity = min(1., max(0., params["Symptoms:Severity"]["Value"]))

    def calculate(self,time):
        if time>self.starttime + self.Toffset and time<self.starttime+self.Tend:
            self.severity = self.maxseverity
        else:
            self.severity = 0
        
#################################################################################
#################################################################################
#################################################################################

class SymptomsGaussian(Symptoms):
    def init(self,params):
        self.maxseverity = min(1., max(0., params["Symptoms:MaximalSeverity"]["Value"]))
        self.Tmean = max(0., params["Symptoms:MeanTime"]["Value"])
        self.sigmaT = max(0.001, params["Symptoms:SigmaTime"]["Value"])
        
    def calculate(self,time):
        dt = time - (self.starttime + self.Tmean)
        self.severity = (self.maxseverity * np.exp(-dt**2/self.sigmaT**2))
            
