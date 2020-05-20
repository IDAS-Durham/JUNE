import numpy as np

from june.infection.symptoms import Symptoms, SymptomTags


class MissingTrajectoryMakerError(BaseException):
    pass


class MissingTrajectoryError(BaseException):
    pass


class MissingPatientError(BaseException):
    pass


class SymptomsTrajectory(Symptoms):
    def __init__(self, health_index=None):
        super().__init__(health_index=health_index)

    def make_trajectory(self, trajectory_maker, patient):
        maxtag = self.max_tag()
        if trajectory_maker == None:
            raise MissingTrajectoryMakerError(
                f"SymptomsTrajectory instantiated without patient"
            )
        if patient == None:
            raise MissingPatientError(
                f"SymptomsTrajectory instantiated without patient"
            )
        self.trajectory = trajectory_maker[maxtag, patient]

    def max_tag(self):
        index = np.searchsorted(self.health_index, self.max_severity)
        return SymptomTags(index + 2)

    def update_severity_from_delta_time(self, delta_time):
        self.tag = SymptomTags.healthy
        if self.trajectory == []:
            raise MissingTrajectoryMakerError(
                f"SymptomsTrajectory has no trajectory"
            )
        for stage in self.trajectory:
            if delta_time > stage[0]:
                self.tag = stage[1]
            if delta_time < stage[0]:
                break
