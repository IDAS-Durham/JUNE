from covid.parameters import ParameterInitializer
import numpy as np
import random

ALLOWED_SYMPTOM_TAGS = [
    "asymptomatic",
    "influenza-like illness",
    "pneumonia",
    "hospitalised",
    "intensive care",
    "dead",
]


class Symptoms(ParameterInitializer):
    def __init__(self, timer, health_index, user_parameters, required_parameters):
        super().__init__("symptoms", user_parameters, required_parameters)
        self.timer                = timer
        self.infection_start_time = self.timer.now
        self.last_time_updated    = self.timer.now  # for testing
        self.health_index         = health_index
        self.maxseverity          = 0.9+0.1*random.random()
        self.tags                 = ALLOWED_SYMPTOM_TAGS
        self.severity             = 0.0

    def update_severity(self):
        self.last_time_updated = self.timer.now
        pass

    def is_recovered(self):
        pass

    @property
    def n_tags(self):
        return len(self.tags)

    @property
    def tag(self):
        return self.fix_tag()

    def fix_tag(self):
        if self.severity <= 0.0:
            return "healthy"
        index = np.searchsorted(self.health_index, self.severity)
        tag = self.tags[index]
        return tag
