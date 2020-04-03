import numpy as np
import random

class Transmission:
    """
    The probability for an individual to transmit the infection.
    This is time-dependent, and the actual value is calculated in the method
    Probability.  We allow to vary parameters around their mean value with
    a left- and right-sided Gaussian described by sigma and the result
    limited by 2 sigma in either direction or physical limits.  

    Currently two forms are implemented:
    - TransmissionSI
    a constant transmission probability, given by the value, with infinite length
    The only parameter is Transmission::Probability
    - TransmissionConstantInterval
    a constant transmission probability, given by the value and the length
    of the transmission period.
    Parameters are Transmission:Probability and Transmission:EndTime
    - TransmissionXNExp
    a probablity of the form $P(t) = P_0 x^n exp(-x/a)$ with parameters given
    by P_0 = Transmission:Probability, n = Transmission:Exponent, and 
    a = Transmission:Norm 

    TODO: we should try and map this onto the Flute/Imperial models, as far
    as possible, to have a baseline and to facilitate validation.
    """
    def __init__(self,person,params={},time=-1.):
        self.person    = person
        self.starttime = time
        self.value     = 0.
        self.init(params)

    def init(self,params):
        pass
    
    def probability(self,time):
        if time >= self.starttime:
            self.calculate(time)
        else:
            self.value = 0.
        return max(0.,self.value)

    def calculate(self,time):
        pass

#################################################################################
#################################################################################
#################################################################################

class TransmissionSI(Transmission):
    def init(self,params):
        self.prob = min(1.,max(0.,params["Transmission:Probability"]["Value"]))

    def calculate(self,time):
        self.value = self.prob
        
#################################################################################
#################################################################################
#################################################################################

class TransmissionSIR(Transmission):
    def init(self,params):
        self.probT = min(1.,max(0.,params["Transmission:Probability"]["Value"]))
        self.probR = min(1.,max(0.,params["Transmission:Recovery"]["Value"]))
        self.lasttime = 0 # last time they had a chance to recover

    def calculate(self,time):
        if self.probT>0 and time>self.lasttime:
            for t in range(self.lasttime, time, 1):
                is_recovered = random.random() < self.probR
                if is_recovered:
                    self.probT = 0 # can't transmit anymore
                    self.person.set_susceptibility(0) # immune
                    self.person.set_recovered(is_recovered)
                    break # can only recover one time
            self.lasttime = time # update last time
        self.value = self.probT
        
#################################################################################
#################################################################################
#################################################################################

    
class TransmissionConstantInterval(Transmission):
    def init(self,params):
        self.prob    = min(1.,max(0.,params["Transmission:Probability"]["Value"]))
        self.endtime = params["Transmission:EndTime"]["Value"]
        self.value   = 0
        
    def calculate(self,time):
        if time<=self.starttime+self.endtime:
            self.value = self.prob
        else:
            self.value = 0.

#################################################################################
#################################################################################
#################################################################################

class TransmissionXNExp(Transmission):
    def init(self,params):
        self.prob       = min(1.,max(0.,params["Transmission:Probability"]["Value"]))
        self.exponent   = max(0.,params["Transmission:Exponent"]["Value"])
        self.tailfactor = params["Transmission:Norm"]["Value"]
        if self.tailfactor  < 0.001:
            self.tailfactor = 0.001
        self.init_norm

    def init_norm(self):
        x0        = self.exponent * self.tailfactor
        self.norm = x0**self.exponent * np.exp(-x0/self.tailfactor)  
        self.norm = 1./self.norm
                               
    def calculate(self,time):
        dt = time - self.starttime
        self.value = (self.norm * self.prob *
                     dt**self.exponent *
                     np.exp(-dt/self.tailfactor))
    

