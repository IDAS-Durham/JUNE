import random
import numpy as np
from scipy import stats
from june.infection.symptoms import Symptoms 
from enum import IntEnum
import autofit as af
import sys

ALLOWED_SYMPTOM_TAGS = [
    "asymptomatic",
    "influenza-like illness",
    "pneumonia",
    "hospitalised",
    "intensive care",
    "dead",
]

class VariationType(IntEnum):
    constant  = 0,
    gaussian  = 1,
    lognormal = 2

    
class TrajectoryMaker:
    class TimeSetter:
        def make_time(params):
            if params[0]==VariationType.constant:
                return params[2]
            elif params[0]==VariationType.gaussian:
                return self.Gaussian(params[2],params[3])
            elif params[0]==VariationType.lognormal:
                return self.LogNormal(params[2],params[3])
            else:
                print("Variation method not yet implemented:",params[0])

        def Gaussian(self,mean,width):
            raise NotImplementedError()

        def LogNormal(self,mean,width):
            raise NotImplementedError()

    """
    The various trajectories should depend on external data, and may depend on age &
    gender of the patient.  This would lead to a table of tons of trajectories, with
    lots of mean values/deviations and an instruction on how to vary them.
    For this first simple implementation I will choose everything to be fixed (constant)

    The trajectories will count "backwards" with zero time being the moment of
    infection.
    """
    def __init__(self, parameters):
        self.trajectories = {}
        self.init_tables(parameters)
        
    def __getitem__(self,tag):
        template   = self.trajectories[tag]
        cumulative = 0.
        trajectory = []
        for stage in template:
            time = self.TimeSetter.make_time(stage)
            cumulative += time
            trajectory.append([cumulative,stage[1]])
        return trajectory
        
    def init_tables(self,parameters):
        self.incubation_info = self.FillIncubationTime(parameters)
        for tag in ALLOWED_SYMPTOM_TAGS:
            if tag=="asymptomatic":
                self.trajectories[tag] = self.FillAsymptomaticTrajectory(parameters)
            elif tag=="influenza-like illness":
                self.trajectories[tag] = self.FillInfluenzaLikeTrajectory(parameters)
            elif tag=="hospitalised":
                self.trajectories[tag] = self.FillHospitalisedTrajectory(parameters)
            elif tag=="intensive care":
                self.trajectories[tag] = self.FillIntensiveCareTrajectory(parameters)
            elif tag=="dead":
                self.trajectories[tag] = self.FillDeathTrajectory(parameters)
                
    def FillIncubationTime(self,parameters):
        incubation_time = 5.1  #parameters["incubation_time"] etc.
        return [VariationType.constant,"asymptomatic",incubation_time]
        
    def FillAsymptomaticTrajectory(self,parameters):
        recovery_time = 14.    #parameters["asymptomatic_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,"asymptomatic",recovery_time]]
    
    def FillInfluenzaLikeTrajectory(self,parameters):
        recovery_time = 20.    #parameters["influenza_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,"influenza-like illness",recovery_time]]
    
    def FillHospitalisedTrajectory(self,parameters):
        prehospital_time = 2.  #parameters["pre_hospital_time"] etc.
        recovery_time    = 20. #parameters["hospital_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,"influenza-like illness",prehospital_time],
                [VariationType.constant,"hospitalised",recovery_time]]    
    
    def FillIntensiveCareTrajectory(self,parameters):
        prehospital_time = 2.  #parameters["pre_hospital_time"] etc.
        hospital_time    = 2.  #parameters["hospital_time"] etc.
        ICU_time         = 20. #parameters["intensive_care_time"] etc.
        recovery_time    = 20. #parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,"influenza-like illness",prehospital_time],
                [VariationType.constant,"hospitalised",prehospital_time],
                [VariationType.constant,"intensive care",ICU_time],    
                [VariationType.constant,"hospitalised",recovery_time]]        
    
    def FillDeathTrajectory(self,parameters):
        prehospital_time = 2.  #parameters["pre_hospital_time"] etc.
        hospital_time    = 2.  #parameters["hospital_time"] etc.
        ICU_time         = 10. #parameters["intensive_care_time"] etc.
        death_time       = 0.  #parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,"influenza-like illness",prehospital_time],
                [VariationType.constant,"hospitalised",hospital_time],
                [VariationType.constant,"intensive care",ICU_time],
                [VariationType.constant,"death",death_time]]        

class SymptomsTrajectory(Symptoms):
    def __init__(self, health_index=0.):
        super().__init__(health_index=health_index)
        self.trajectory = self.make_trajectory()

    def make_trajectory(self):
        maxtag   = self.max_tag(self.max_severity)
        tmaker   = TrajectoryMaker(None)
        return tmaker[maxtag]
        
    def max_tag(self,severity):
        index = np.searchsorted(self.health_index, self.max_severity)
        return self.tags[index]
        
    def update_severity_from_delta_time(self, time):
        pass

    def is_recovered(self):
        pass


