import random

import numpy as np
from june.infection.symptom_tag import SymptomTag
from june.infection.trajectory_maker import TrajectoryMakers


class Symptoms:
    def __init__(self, health_index=None):
        self.health_index = list() if health_index is None else health_index
        self.tag = SymptomTag.exposed
        self.max_severity = random.random()
        self.trajectory = None
        self.update_trajectory()
        self.stage = 0
        self.tag = self.trajectory[self.stage][1]

    def time_from_infection_to_symptoms(self):
        symptoms_onset = 0
        for completion_time, tag in self.trajectory:
            symptoms_onset += completion_time
            if tag == SymptomTag.mild:
                break
            elif tag == SymptomTag.asymptomatic:
                return None
        return symptoms_onset

    def time_exposed(self):
        return self.trajectory[1][0]

    def is_recovered(self):
        return self.tag == SymptomTag.recovered

    def update_trajectory(self):
        trajectory_maker = TrajectoryMakers.from_file()
        maxtag = self.max_tag()
        self.trajectory = trajectory_maker[maxtag]

    def max_tag(self):
        index = np.searchsorted(self.health_index, self.max_severity)
        return SymptomTag(index)

    def update_severity_from_delta_time(self, time_from_infection):
        if time_from_infection > self.trajectory[self.stage + 1][0]:
            self.stage += 1
            self.tag = self.trajectory[self.stage][1]
