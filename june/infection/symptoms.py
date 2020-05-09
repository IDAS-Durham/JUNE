import random

import numpy as np
from scipy import stats

ALLOWED_SYMPTOM_TAGS = [
    "asymptomatic",
    "influenza-like illness",
    "pneumonia",
    "hospitalised",
    "intensive care",
    "dead",
]



class Symptoms:
    def __init__(self, health_index=0.):

        self.severity = 0
        self.health_index = health_index
        self.maxseverity = random.random()
        self.tags = ALLOWED_SYMPTOM_TAGS
        self.severity = 0.0

    def update_severity_from_delta_time(self, time):
        raise NotImplementedError()

    def is_recovered(self):
        raise NotImplementedError()

    @property
    def tag(self):
        if self.severity <= 0.0:
            return "healthy"
        index = np.searchsorted(self.health_index, self.severity)-1
        return self.tags[index]


class SymptomsConstant(Symptoms):
    def __init__(self, health_index=0., recovery_rate=0.2):
        super().__init__(health_index=health_index)

        self.recovery_rate = recovery_rate
        self.predicted_recovery_time = stats.expon.rvs(scale=1.0 / self.recovery_rate)

    def update_severity_from_delta_time(self, delta_time):

        pass

    def is_recovered(self, delta_time):
        prob_recovery = 1.0 - np.exp(-self.recovery_rate * delta_time)
        return np.random.rand() <= prob_recovery


class SymptomsGaussian(Symptoms):
    #TODO: Add recovery_theshold for recovery, and check parameters to find days to recover
    def __init__(self, health_index=0., mean_time=1.0, sigma_time=3.0, recovery_rate=0.05):
        super().__init__(health_index=health_index)

        self.mean_time = max(0.0, mean_time)
        self.sigma_time = max(0.001, sigma_time)
        self.maxseverity = random.random()
        self.recovery_rate = recovery_rate

    def update_severity_from_delta_time(self, delta_time):

        dt = delta_time - self.mean_time

        self.severity = self.maxseverity * np.exp(-(dt ** 2) / self.sigma_time ** 2)
    
    def is_recovered(self, delta_time):
        prob_recovery = 1.0 - np.exp(-self.recovery_rate * delta_time)
        return np.random.rand() <= prob_recovery


class SymptomsStep(Symptoms):
    def __init__(self, health_index=0., time_offset=2.0, end_time=5.0):

        super().__init__(health_index)

        self.time_offset = max(0.0, time_offset)
        self.end_time = max(0.0, end_time)
        self.maxseverity = random.random()

    def update_severity_from_delta_time(self, delta_time):

        if self.time_offset < delta_time < self.end_time:
            severity = self.maxseverity
        else:
            severity = 0.0

        self.severity = severity


class SymptomsTanh(Symptoms):
    def __init__(self, health_index=0., max_time=2.0, onset_time=0.5, end_time=15.0):

        super().__init__(health_index)

        self.max_time = max(0.0, max_time)
        self.onset_time = max(0.0, onset_time)
        self.end_time = max(0.0, end_time)
        self.delta_onset = self.max_time - self.onset_time
        self.delta_end = self.end_time - self.max_time

    def update_severity_from_delta_time(self, delta_time):

        # TODO : These have both cropped up in the recent project history, which is correct?

        if delta_time <= self.max_time:
            severity = (
                1.0
                + np.tanh(np.pi * (delta_time - self.onset_time) / self.delta_onset)
            ) / 2.0
        else:
            severity = (
                1.0 + np.tanh(np.pi * (self.end_time - delta_time) / self.delta_end)
            ) / 2.0

        print(severity)

        severity *= self.maxseverity
        self.severity = severity
