import numpy as np
import random
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
    def __init__(self, health_index):

        self.severity = 0
        self.last_time_updated = 0
        self.health_index = health_index
        self.maxseverity = random.random()
        self.tags = ALLOWED_SYMPTOM_TAGS
        self.severity = 0.0

    def update_severity(self, time):
        self.last_time_updated = time

    def is_recovered(self):
        raise NotImplementedError()

    @property
    def tag(self):
        if self.severity <= 0.0:
            return "healthy"
        index = np.searchsorted(self.health_index, self.severity)
        return self.tags[index]



class SymptomsConstant(Symptoms):

    def __init__(self, timer, health_index, user_parameters=None):
        user_parameters = user_parameters or dict()
        required_parameters = ["recovery_rate"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.predicted_recovery_time = self.predict_recovery_time()

    def predict_recovery_time(self):
        """If the probabiliy of recovery per day is p, then the recovery day can be estimaed by sampling from a geometric distribution with parameter p."""
        days_to_recover = stats.expon.rvs(scale=1.0 / self.recovery_rate)
        # day_of_recovery = self.timer.now + days_to_recover
        return days_to_recover

    def is_recovered(self):
        deltat = self.timer.now - self.timer.previous
        prob_recovery = 1.0 - np.exp(-self.recovery_rate * deltat)
        if np.random.rand() <= prob_recovery:
            return True
        else:
            return False

    def update_severity(self):
        pass


class SymptomsGaussian(Symptoms):
    def __init__(self, timer, health_index, user_parameters={}):
        required_parameters = ["mean_time", "sigma_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.Tmean = max(0.0, self.mean_time)
        self.sigmaT = max(0.001, self.sigma_time)

    def update_severity(self):
        time = self.timer.now
        dt = time - (self.start_time + self.Tmean)
        self.last_time_updated = time
        self.severity = self.maxseverity * np.exp(-(dt ** 2) / self.sigmaT ** 2)


class SymptomsStep(Symptoms):
    def __init__(self, timer, health_index, user_parameters=None):
        user_parameters = user_parameters or dict()
        required_parameters = ["time_offset", "end_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)
        self.time_offset = max(0.0, self.time_offset)
        self.end_time = max(0.0, self.end_time)

    def update_severity(self):
        time = self.timer.now
        if (
            time > self.start_time + self.time_offset
            and time < self.start_time + self.end_time
        ):
            severity = self.maxseverity
        else:
            severity = 0.0

        self.last_time_updated = time
        self.severity = severity


class SymptomsTanh(Symptoms):
    def __init__(self, timer, health_index, user_parameters=None):
        user_parameters = user_parameters or dict()
        required_parameters = ["max_time", "onset_time", "end_time"]
        super().__init__(timer, health_index, user_parameters, required_parameters)

        self.Tmax = max(0.0, self.max_time)
        self.Tonset = max(0.0, self.onset_time)
        self.Tend = max(0.0, self.end_time)
        self.delta_onset = self.Tmax - self.Tonset
        self.delta_end = self.Tend - self.Tmax

    def update_severity(self):
        time = self.timer.now
        self.severity = 0.0
        time_since_start = time - self.start_time
        if time_since_start <= self.Tmax:
            severity = (
                1.0
                + np.tanh(3.14 * (time_since_start - self.Tonset) / self.delta_onset)
            ) / 2.0
        elif time_since_start > self.Tmax:
            severity = (
                1.0 + np.tanh(3.14 * (self.Tend - time_since_start) / self.delta_end)
            ) / 2.0
        elif time > self.Tend:
            severity = 0.0
        severity *= self.maxseverity
        self.last_time_updated = time
        self.severity = severity