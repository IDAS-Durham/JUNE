import autofit as af
import numpy as np
import sys


class Transmission:
    def __init__(self):
        self.probability = 0.0
        
    def update_probability_from_delta_time(self, delta_time):
        raise NotImplementedError()

    @classmethod
    def object_from_config(cls):
        """
        Loads the default Transmission class from the general.ini config file and 
        returns the class as object (not as an instance). This is used to set up the 
        epidemiology model in world.py via configs if an input is not provided.
        """
        classname_str = af.conf.instance.general.get("epidemiology", "transmission_class", str)
        return getattr(sys.modules[__name__], classname_str)
    
class TransmissionConstant(Transmission):
    def __init__(self, probability=0.3):
        super().__init__()
        self.probability = probability

    def update_probability_from_delta_time(self, delta_time):
        pass
