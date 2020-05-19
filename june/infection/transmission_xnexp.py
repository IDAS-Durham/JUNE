from june.infection.transmission import Transmission
import numpy as np

class TransmissionXNExp(Transmission):
    def __init__(self,
                 max_probability = 1.0,
                 incubation_time = 2.6,
                 norm_time = 1., N = 1., alpha = 5.):
        self.max_probability = max_probability
        self.incubation_time = incubation_time
        self.norm_time = norm_time
        self.N         = N
        self.alpha     = alpha
        max_time       = self.N * self.alpha * self.norm_time
        self.norm      = self.max_probability/self.f(max_time/self.norm_time)  #/self.norm_time)
        self.probability = 0
        
    def update_probability_from_delta_time(self, delta_time):
        if delta_time<=self.incubation_time:
            self.probability = 0.
        else:
            delta_tau = (delta_time - self.incubation_time)/self.norm_time
            self.probability = self.norm * self.f(delta_tau)

    def f(self,t):
        return t**self.N * np.exp(-t/self.alpha)
