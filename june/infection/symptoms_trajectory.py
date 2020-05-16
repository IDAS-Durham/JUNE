from june.infection.symptoms import Symptoms
from june.infection.trajectory_maker import Trajectory_Maker as TM
import numpy as np

class MissingTrajectoryMakerError(BaseException):
    pass

class MissingPatientError(BaseException):
    pass
    
class SymptomsTrajectory(Symptoms):
    def __init__(self, health_index=None, patient=None):
        super().__init__(health_index=health_index)
        
    def make_trajectory(self,trajectory_maker,patient):
        maxtag = self.max_tag(self.max_severity)
        if patient==None:
            raise MissingPatientError(
                f"SymptomsTrajectory instantiated without patient"
            )
        self.trajectory = TM[maxtag,patient]
        
    def max_tag(self,severity):
        index = np.searchsorted(self.health_index, self.max_severity)
        return Symptom_Tags(index+2)
        
    def update_severity_from_delta_time(self, delta_time):
        self.tag = Symptom_Tags.healthy
        for stage in self.trajectory:
            if delta_time>stage[0]:
                self.tag = stage[1]
            if delta_time<stage[0]:
                break
