import numpy as np
import random
import sys
import covid.transmission as Transmission
import covid.symptoms as Symptoms

class Infection:
    def __init__(self, config):
        self.init_transmission()
        self.init_symptoms()

    def still_infected(self, time):
        pass
        #transmission_bool = (
        #    self.transmission.probability(time) > self.threshold_transmission
        #)
        #symptoms_bool = (
        #    self.symptoms.get_severity(time) > self.threshold_symptoms
        #)
        #is_infected = transmission_bool or symptoms_bool
        #return is_infected

    def init_transmission(self):
        pass
    
    def init_symptoms(self):
        pass


