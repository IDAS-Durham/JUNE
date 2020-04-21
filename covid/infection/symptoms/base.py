from covid.parameters import ParameterInitializer
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
    def __init__(self, timer, health_index, user_parameters, required_parameters):
        super().__init__("symptoms", required_parameters)
        self.initialize_parameters(user_parameters)
        self.timer = timer
        self.starttime = self.timer.now
        self.health_index = health_index
        self.maxseverity = random.random()
        self.tags = allowed_symptom_tags

    @property
    def severity(self):
        if self.timer.now >= self.starttime:
            severity  = self._calculate_severity(self.timer.now)
        else:
            severity = 0.0
        return max(0.0, severity)

    @property
    def n_tags(self):
        return len(self.tags)

    @property
    def tag(self):
        return self.fix_tag(self.severity)

    def fix_tag(self, severity):
        if severity <= 0.0:
            return "healthy"
        index = np.searchsorted(self.health_index, severity)
        return self.tags[index + 1]

    def tags(self):
        return self.tags
