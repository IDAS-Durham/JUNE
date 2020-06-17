import numpy as np

from june.infection.symptoms import Symptoms, SymptomTag
from june.infection.trajectory_maker import TrajectoryMakers


class SymptomsTrajectory(Symptoms):
    @property
    def severity(self):
        return self.trajectory[self.stage][1]

    def __init__(self, health_index=None):
        super().__init__(health_index=health_index)
        self.trajectory = None
        self.update_trajectory()
        self.stage = 0
        self.tag = self.trajectory[self.stage][1]

    def update_trajectory(self):
        trajectory_maker = TrajectoryMakers.from_file()
        maxtag = self.max_tag()
        self.trajectory = trajectory_maker[maxtag]

    def max_tag(self):
        index = np.searchsorted(self.health_index, self.max_severity)
        return SymptomTag(index)

    def update_severity_from_delta_time(self, delta_time):
        print(self.trajectory)
        print(self.stage)
        if delta_time > self.trajectory[self.stage+1][0]:
            self.stage += 1
            self.tag = self.trajectory[self.stage][1]
