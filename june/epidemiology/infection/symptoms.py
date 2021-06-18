from random import random

import numpy as np
from .symptom_tag import SymptomTag
from .trajectory_maker import TrajectoryMakers

dead_tags = (SymptomTag.dead_home, SymptomTag.dead_hospital, SymptomTag.dead_icu)


class Symptoms:
    __slots__ = (
        "tag",
        "max_tag",
        "max_severity",
        "trajectory",
        "stage",
        "time_of_symptoms_onset",
    )
    """
    Class to represent the symptoms of a person. The symptoms class composes the
    ``Infection`` class alongside with the ``Transmission`` class. Once infected,
    a person is assigned a symptoms trajectory according to a health index generated
    by the ``HealthIndexGenerator``. A trajectory is a collection of symptom tags with
    characteristic timings.
    """

    def __init__(self, health_index=None):
        self.max_tag = None
        self.tag = SymptomTag.exposed
        self.max_severity = random()
        self.trajectory = self._make_symptom_trajectory(
            health_index
        )  # this also sets max_tag
        self.stage = 0
        self.time_of_symptoms_onset = self._compute_time_from_infection_to_symptoms()

    def _compute_time_from_infection_to_symptoms(self):
        symptoms_onset = 0
        for completion_time, tag in self.trajectory:
            symptoms_onset += completion_time
            if tag == SymptomTag.mild:
                break
            elif tag == SymptomTag.asymptomatic:
                return None
        return symptoms_onset

    def _make_symptom_trajectory(self, health_index):
        if health_index is None:
            return [(0, SymptomTag(0))]
        trajectory_maker = TrajectoryMakers.from_file()
        index_max_symptoms_tag = np.searchsorted(health_index, self.max_severity)
        self.max_tag = SymptomTag(index_max_symptoms_tag)
        return trajectory_maker[self.max_tag]

    def update_trajectory_stage(self, time_from_infection):
        """
        Updates the current symptom tag from the symptoms trajectory,
        given how much time has passed since the person was infected.

        Parameters
        ----------
        time_from_infection: float
            Time in days since the person got infected.
        """
        if time_from_infection > self.trajectory[self.stage + 1][0]:
            self.stage += 1
            self.tag = self.trajectory[self.stage][1]

    @property
    def time_exposed(self):
        return self.trajectory[1][0]

    @property
    def recovered(self):
        return self.tag == SymptomTag.recovered

    @property
    def dead(self):
        return self.tag in dead_tags
