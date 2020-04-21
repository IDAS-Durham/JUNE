import numpy as np
import random
import sys
import os
import yaml
import importlib
from covid.infection.transmission import *
from covid.infection.symptoms import *
from covid.parameters import ParameterInitializer


class InfectionInitializer:
    def __init__(self, timer, health_index, user_config):
        infection_name = type(self).__name__
        self.timer = timer
        user_config = user_config
        default_types = self.read_default_config(infection_name)
        self.transmission = self.initialize_transmission(default_types, user_config)
        self.symptoms = self.initialize_symptoms(
            health_index, default_types, user_config
        )

    def read_default_config(self, infection_name):
        default_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "..",
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
            print(default_path)
            raise FileNotFoundError("Default parameter config file not found")
        return default_params

    def initialize_transmission(self, default_types, user_config):
        if "transmission" in user_config:
            transmission_type = user_config["transmission"]["type"]
            if "parameters" in user_config["transmission"]:
                transmission_parameters = user_config["transmission"]["parameters"]
            else:
                transmission_parameters = {}
        else:
            transmission_type = default_types["transmission"]["type"]
            transmission_parameters = {}
        transmission_class_name = "Transmission" + transmission_type.capitalize()
        transmission = globals()[transmission_class_name](
            self.timer, transmission_parameters
        )
        return transmission

    def initialize_symptoms(self, health_index, default_types, user_config):
        if "symptoms" in user_config:
            symptoms_type = user_config["symptoms"]["type"]
            if "parameters" in user_config["symptoms"]:
                symptoms_parameters = user_config["symptoms"]["parameters"]
            else:
                symptoms_parameters = {}
        else:
            symptoms_type = default_types["symptoms"]["type"]
            symptoms_parameters = {}
        symptoms_class_name = "Symptoms" + symptoms_type.capitalize()
        symptoms = globals()[symptoms_class_name](
            self.timer, health_index, symptoms_parameters
        )
        return symptoms


class Infection(InfectionInitializer, ParameterInitializer):
    """
    The description of the infection, with two time dependent characteristics,
    which may vary by individual:
    - transmission probability, Ptransmission.
    - symptom severity, Severity
    Either of them will be a numer between 0 (low) and 1 (high, strong sypmotoms), 
    and for both we will have some thresholds.
    Another important part for the infection is their begin, starttime, which must
    be given in the constructor.  Transmission probability and symptom severity
    can be added/modified a posteriori.
    """

    def __init__(self, person, timer, user_config, required_parameters):
        self.person = person
        if person == None:
            InfectionInitializer.__init__(timer, None, user_config)
        else:
            InfectionInitializer.__init__(timer, self.person.health_index, user_config)
        ParameterInitializer.__init__("infection", required_parameters)
        try:
            self.starttime = timer.now
        except:
            print("is this a test? otherwise check the time!")
            pass
        self.user_config = user_config
        self.last_time_updated = self.timer.now  # testing
        self.infection_probability = 0.0

    def infect(self, person_to_infect):
        person_to_infect.infection = Infection(
            person_to_infect, self.timer, self.user_config
        )

    def set_transmission(self, transmission):
        if not isinstance(transmission, Transmission):
            print(
                "Error in Infection.set_transmission(",
                transmission,
                ") is not a transmission.",
            )
            print("--> Exit the code.")
            sys.exit()
        self.transmission = transmission

    def set_symptoms(self, symptoms):
        if symptoms != None and not isinstance(symptoms, Symptoms):
            print("Error in Infection.set_symptoms(", symptoms, ") is not a symptoms.")
            print("--> Exit the code.")
            sys.exit()
        self.symptoms = symptoms

    def symptom_tag(self, tagno):
        return self.symptoms.tag

    @property
    def still_infected(self):
        transmission_bool = (
            self.transmission != None
            and self.transmission.probability > self.threshold_transmission
        )
        symptoms_bool = (
            self.symptoms != None and self.symptoms.severity > self.threshold_symptoms
        )
        is_infected = transmission_bool or symptoms_bool
        return is_infected

    def update_infection_probability(self):
        self.last_time_updated = self.timer.now
        # do something here to realte transmission probability and symptoms


if __name__ == "__main__":
    user_params = {
        "transmission": {"type": "constant"},
        "symptoms": {"type": "tanh"},
    }
    inf = Infection(None, None, user_params)
    print(inf.transmission)
    print(inf.symptoms.infection)
    print(inf.transmission.probability)
