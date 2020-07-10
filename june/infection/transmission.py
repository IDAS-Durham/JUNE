from june.infection.trajectory_maker import CompletionTime
from june import paths
import autofit as af
import yaml
import numpy as np
import sys


default_config_path = paths.configs_path / "defaults/transmission/TransmissionConstant.yaml"
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

    @classmethod
    def from_file(cls, config_path: str  = default_config_path) -> "TransmissionConstant":
        with open(config_path) as f:
            config = yaml.safe_load(f)
        probability = CompletionTime.from_dict(config['probability'])()
        return TransmissionConstant(probability=probability)


 
    def update_probability_from_delta_time(self, delta_time):
        pass
