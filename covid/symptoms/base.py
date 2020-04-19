from covid.parameters import ParameterInitializer
#from covid.infection import Infection
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


class Symptoms(ParameterInitializer):
    def __init__(self, infection, user_parameters, required_parameters):
        self.infection = infection
        super().__init__("symptoms", required_parameters)
        self.initialize_parameters(user_parameters)
        #self.infection = self.set_infection(infection)
        self.maxseverity = random.random()
        self.tags = allowed_symptom_tags
        #self.health_index = self.infection.person.get_health_index()

    def set_infection(self, infection):
        if not isinstance(infection, Infection):
            print(
                "Error in Symptoms.set_infection(", infection, ") is not an infection.",
            )
            print("--> Exit the code.")
            sys.exit()
        self.infection = infection

    @property
    def severity(self):
        if self.infection.timer.now >= self.infection.starttime:
            severity  = self._calculate_severity(self.infection.timer.now)
        else:
            severity = 0.0
        return max(0.0, severity)

    @property
    def n_tags(self):
        return len(self.tags)

    @property
    def tag(self):
        self.calculate(self.timer.now)
        return self.fix_tag(self.severity)

    def fix_tag(self, severity):
        if severity <= 0.0:
            return "healthy"
        index = len(self.health_index) - 1
        while severity <= self.health_index[index] and index >= 0:
            index -= 1
        return self.tags[index + 1]

    def tags(self):
        return self.tags
