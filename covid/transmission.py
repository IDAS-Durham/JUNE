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
    - TransmissionConstantInterval
    a constant transmission probability, given by the value and the length
    of the transmission period.
    Parameters are Transmission:MeanProb and Transmission:EndTime, with widths
    Transmission:MeanProbUpper and Transmission:MeanProbLower and similar for the
    end time.
    - TransmissionXNExp
    a probablity of the form $P(t) = P_0 x^n exp(-x/a)$ with parameters given
    by P_0 = Transmission:MeanProb, n = Transmission:Exponent, and 
    a = Transmission:Norm 

    TODO: we should try and map this onto the Flute/Imperial models, as far
    as possible, to have a baseline and to facilitate validation.
    """
    def __init__(self,params={},time=-1.):
        self.starttime = time
        self.prob      = 0.
        self.Init(params)

    def SetInterval(self,interval):
        pass

    def ResetParameters(self):
        pass
    
    def SetParameter(self,param,limits):
        delta = -1.
        while delta < 0. or delta>2. or paramnew > limits[1] or paramnew < limits[0]:
            delta = random.gauss(0.,1.)
            if random.random() < param[1]/(param[1]+param[2]):
                paramnew = param[0] + delta * param[1]
            else:
                paramnew = param[0] - delta * param[2]
        return paramnew

    def SmearingFunction(self,x,param):
        if x <= param[0]:
            return np.exp(-(x-param[0])**2/param[2])
        else:
            return np.exp(-(x-param[0])**2/param[1])
    
    def Init(self,params):
        pass
    
    def Probability(self,time):
        if time > self.starttime:
            self.Calculate(time)
        else:
            self.prob = 0.
        return max(0.,self.prob)

    def Calculate(self,time):
        pass


#################################################################################
#################################################################################
#################################################################################
    
class NoTransmission(Transmission):
    pass

#################################################################################
#################################################################################
#################################################################################


class TransmissionConstantInterval(Transmission):
    def Init(self,params):
        self.meanprobs = []
        self.endtimes = []
        self.meanprobs.append(params["Transmission:MeanProb"])
        self.endtimes.append(params["Transmission:EndTime"])
        self.ResetParameters()
        
    def Calculate(self,time):
        if time <= self.starttime+self.endtime and time>=self.starttime:
            self.prob = self.meanprob
        else:
            self.prob = 0.

    def SetInterval(self,params):
        self.meanprobs.append(params["Transmission:MeanProbUpper"])
        self.meanprobs.append(params["Transmission:MeanProbLower"])
        self.endtimes.append(params["Transmission:EndTimeUpper"])
        self.endtimes.append(params["Transmission:EndTimeLower"])

    def ResetParameters(self):
        self.meanprob = self.meanprobs[0]
        self.endtime = self.endtimes[0]
    
    def SetParameters(self):
        limits = [0,1]
        self.meanprob = Transmission.SetParameter(self,self.meanprobs,limits)
        limits = [0,2*self.endtimes[0]]
        self.endtime = Transmission.SetParameter(self,self.endtimes,limits)

    def EndTime(self):
        return self.endtime
        
    def MeanProb(self):
        return self.meanprob


#################################################################################
#################################################################################
#################################################################################

class TransmissionXNExp(Transmission):
    def Init(self,params):
        self.meanprobs    = []
        self.exponents   = []
        self.tailfactors = []
        self.meanprobs.append(params["Transmission:MeanProb"])
        self.exponents.append(params["Transmission:Exponent"])
        self.tailfactors.append(params["Transmission:Norm"])
        if self.exponents[0]    < 0.:
            self.exponents[0]   = 0.;
        if self.meanprobs[0]     > 1.:
            self.meanprobs[0]    = 1.
        if self.tailfactors[0]  < 0.001:
            self.tailfactors[0] = 0.001
        self.ResetParameters()

    def InitNorm(self):
        x0        = self.exponent * self.tailfactor
        self.norm = x0**self.exponent * np.exp(-x0/self.tailfactor)  
        self.norm = 1./self.norm
        
    def ResetParameters(self):
        self.meanprob    = self.meanprobs[0]
        self.exponent   = self.exponents[0]
        self.tailfactor = self.tailfactors[0]
        self.InitNorm()
        
    def SetInterval(self,params):
        self.meanprobs.append(params["Transmission:MeanProbUpper"])
        self.meanprobs.append(params["Transmission:MeanProbLower"])
        self.exponents.append(params["Transmission:ExponentUpper"])
        self.exponents.append(params["Transmission:ExponentLower"])
        self.tailfactors.append(params["Transmission:NormUpper"])
        self.tailfactors.append(params["Transmission:NormLower"])

    def SetParameters(self):
        limits = [0,1]
        self.meanprob = Transmission.SetParameter(self,self.meanprobs,limits)
        limits = [0.5,2*self.exponents[0]]
        self.exponent = Transmission.SetParameter(self,self.exponents,limits)
        limits = [0.5,2*self.tailfactors[0]]
        self.tailfactor = Transmission.SetParameter(self,self.tailfactors,limits)
        self.InitNorm()
        
    def Calculate(self,time):
        dt = time - self.starttime
        self.prob = (self.norm * self.meanprob *
                     dt**self.exponent *
                     np.exp(-dt/self.tailfactor))
    

