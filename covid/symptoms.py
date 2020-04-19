import numpy as np
import random

allowed_symptom_tags = [
    "none",  # this is only for people who are not ill                        
    "asymptomatic",
    "influenza-like illness",
    "pneumonia",
    "hospitalised",
    "intensive care",
    "dead",
]


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

    # infection
    def __init__(self, person, params, time):
        self.tags         = allowed_symptom_tags
        self.person       = person
        self.health_index = self.person.get_health_index()
        self.starttime    = time
        self.severity     = 0.0
        self.maxseverity  = random.random()
        self.init(params)
        
    def set_interval(self, interval):
        pass

    def reset_parameters(self):
        pass

    def init(self, params):
        pass

    def get_severity(self, time):
        if time >= self.starttime:
            self.calculate(time)
        else:
            self.severity = 0.0
        return max(0.0, self.severity)

    def n_tags(self):
        return len(self.tags)

    def tag(self, time):
        self.calculate(time)
        return fix_tag(self.severity)
    
    def fix_tag(self, severity):
        if severity <= 0.0:
            return "healthy"
        index = len(self.health_index)-1
        while (severity <= self.health_index[index] and
               index >= 0):
            index -= 1        
        return self.tags[index+1]

    def tags(self):
        return self.tags

    def calculate(self, time):
        pass


#################################################################################
#################################################################################
#################################################################################


class SymptomsConstant(Symptoms):
    def init(self, params):
        self.Toffset = max(0.0, params["time_offset"]["value"])
        self.Tend = max(0.0, params["end_time"]["value"])

    def calculate(self, time):
        if time > self.starttime + self.Toffset and time < self.starttime + self.Tend:
            self.severity = self.maxseverity
        else:
            self.severity = 0.


#################################################################################
#################################################################################
#################################################################################


class SymptomsGaussian(Symptoms):
    def init(self, params):
        self.Tmean = max(0.0, params["mean_time"]["value"])
        self.sigmaT = max(0.001, params["sigma_time"]["value"])

    def calculate(self, time):
        dt = time - (self.starttime + self.Tmean)
        self.severity = self.maxseverity * np.exp(-(dt ** 2) / self.sigmaT ** 2)


#################################################################################
#################################################################################
#################################################################################

class SymptomsTanh(Symptoms):
    def init(self,params):
        self.Tmax        = max(0.0, params["max_time"]["value"])
        self.Tonset      = max(0.0, params["onset_time"]["value"])
        self.Tend        = max(0.0, params["end_time"]["value"])
        self.delta_onset = (self.Tmax-self.Tonset)
        self.delta_end   = (self.Tend-self.Tmax)

        
    def calculate(self,time):
        self.severity = 0.
        time_since_start = time - self.starttime
        if time_since_start<=self.Tmax:
            self.severity = (1.+np.tanh(3.14*(time_since_start-self.Tonset)/self.delta_onset))/2.
        elif time_since_start>self.Tmax:
            self.severity = (1.+np.tanh(3.14*(self.Tend-time_since_start)/self.delta_end))/2.
        elif (time>self.Tend):
            self.severity = 0.
        self.severity *= self.maxseverity
        
