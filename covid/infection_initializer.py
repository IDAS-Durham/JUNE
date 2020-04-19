from covid.parameters import ParameterInitializer
from covid.transmission import *
from covid.symptoms import *
import os
import yaml
import importlib

class InfectionInitializer:
    def __init__(self, user_config): 
        infection_name = type(self).__name__
        user_config = user_config
        default_types = self.read_default_config(infection_name)
        self.transmission = self.initialize_transmission(default_types, user_config)
        self.symptoms = self.initialize_symptoms(default_types, user_config)

    def read_default_config(self, infection_name):
        default_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
            "configs",
            "defaults",
            "infection",
            infection_name + ".yaml",
        )
        try:
            with open(default_path, "r") as f:
                default_params = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            raise FileNotFoundError("Default parameter config file not found")
        return default_params

    def initialize_transmission(self, default_types, user_config):
        if "transmission" in user_config:
            transmission_type = user_config["transmission"]["type"]
            if "parameters" in user_config["transmission"]:
                transmission_parameters = user_config["parameters"]
            else:
                transmission_parameters = {}
        else:
            transmission_type = default_types["transmission"]["type"]
        transmission_class_name = "Transmission" + transmission_type.capitalize()
        transmission = globals()[transmission_class_name](transmission_parameters)
        return transmission

    def initialize_symptoms(self, default_types, user_config):
        if "symptoms" in user_config:
            symptoms_type = user_config["symptoms"]["type"]
            if "parameters" in user_config["symptoms"]:
                symptoms_parameters = user_config["parameters"]
            else:
                symptoms_parameters = {}
        else:
            symptoms_type = default_types["symptoms"]["type"]
        symptoms_class_name = "Symptoms" + symptoms_type.capitalize()
        symptoms = globals()[symptoms_class_name](symptoms_parameters)
        return symptoms
