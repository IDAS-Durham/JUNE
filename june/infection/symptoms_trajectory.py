import numpy as np

from june.infection.symptoms import Symptoms, SymptomTags
from june.infection.trajectory_maker import TrajectoryMaker


class SymptomsTrajectory(Symptoms):
    def __init__(self, health_index=None):
        super().__init__(health_index=health_index)
        self.trajectory = None
        self.update_trajectory()

    def update_trajectory(self):
        trajectory_maker = TrajectoryMaker.from_file()
        maxtag = self.max_tag()
        self.trajectory = trajectory_maker[maxtag]

    def max_tag(self):
        index = np.searchsorted(self.health_index, self.max_severity)
        return SymptomTags(index + 2)

    def update_severity_from_delta_time(self, delta_time):
        self.tag = SymptomTags.healthy
        for stage in self.trajectory:
            if delta_time > stage[0]:
                self.tag = stage[1]
            if delta_time < stage[0]:
                break
