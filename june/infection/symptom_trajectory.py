import random
import numpy as np
from scipy import stats
from june.infection.symptoms import Symptoms, Symptom_Tags
from enum import IntEnum
import autofit as af
import sys

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
        template   = self.trajectories[tag[0]]
        cumulative = 0.
        trajectory = []
        for stage in template:
            time = self.TimeSetter.make_time(stage)
            trajectory.append([cumulative,stage[1]])
            cumulative += time
        return trajectory

    def init_tables(self,parameters):
        self.incubation_info = self.FillIncubationTime(parameters)
        self.recovery_info   = self.FillRecoveryInfo()
        for tag in Symptom_Tags:
            if tag==Symptom_Tags.asymptomatic:
                self.trajectories[tag] = self.FillAsymptomaticTrajectory(parameters)
            elif tag==Symptom_Tags.influenza:
                self.trajectories[tag] = self.FillInfluenzaLikeTrajectory(parameters)
            elif tag==Symptom_Tags.pneumonia:
                self.trajectories[tag] = self.FillPneumoniaTrajectory(parameters)
            elif tag==Symptom_Tags.hospitalised:
                self.trajectories[tag] = self.FillHospitalisedTrajectory(parameters)
            elif tag==Symptom_Tags.intensive_care:
                self.trajectories[tag] = self.FillIntensiveCareTrajectory(parameters)
            elif tag==Symptom_Tags.dead:
                self.trajectories[tag] = self.FillDeathTrajectory(parameters)

    def FillIncubationTime(self,parameters):
        incubation_time = 5.1  #parameters["incubation_time"] etc.
        return [VariationType.constant,Symptom_Tags.infected,incubation_time]

    def FillRecoveryInfo(self):
        return [VariationType.constant,Symptom_Tags.recovered,0.0]

        
    def FillAsymptomaticTrajectory(self,parameters):
        recovery_time = 14.    #parameters["asymptomatic_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,Symptom_Tags.asymptomatic,recovery_time],
                self.recovery_info]
    
    def FillInfluenzaLikeTrajectory(self,parameters):
        recovery_time = 20.    #parameters["influenza_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,Symptom_Tags.influenza,recovery_time],
                self.recovery_info]
    
    def FillPneumoniaTrajectory(self,parameters):
        influenza_time = 5.     #parameters["pre_pneumonia_time"] etc.
        recovery_time  = 20.    #parameters["pneumonia_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,Symptom_Tags.influenza,recovery_time],
                [VariationType.constant,Symptom_Tags.pneumonia,recovery_time],
                self.recovery_info]
    
    def FillHospitalisedTrajectory(self,parameters):
        prehospital_time = 2.  #parameters["pre_hospital_time"] etc.
        recovery_time    = 20. #parameters["hospital_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,Symptom_Tags.influenza,prehospital_time],
                [VariationType.constant,Symptom_Tags.hospitalised,recovery_time],
                self.recovery_info]    
    
    def FillIntensiveCareTrajectory(self,parameters):
        prehospital_time = 2.  #parameters["pre_hospital_time"] etc.
        hospital_time    = 2.  #parameters["hospital_time"] etc.
        ICU_time         = 20. #parameters["intensive_care_time"] etc.
        recovery_time    = 20. #parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,Symptom_Tags.influenza,prehospital_time],
                [VariationType.constant,Symptom_Tags.hospitalised,prehospital_time],
                [VariationType.constant,Symptom_Tags.intensive_care,ICU_time],    
                [VariationType.constant,Symptom_Tags.hospitalised,recovery_time],
                self.recovery_info]        
    
    def FillDeathTrajectory(self,parameters):
        prehospital_time = 2.  #parameters["pre_hospital_time"] etc.
        hospital_time    = 2.  #parameters["hospital_time"] etc.
        ICU_time         = 10. #parameters["intensive_care_time"] etc.
        death_time       = 0.  #parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant,Symptom_Tags.influenza,prehospital_time],
                [VariationType.constant,Symptom_Tags.hospitalised,hospital_time],
                [VariationType.constant,Symptom_Tags.intensive_care,ICU_time],
                [VariationType.constant,Symptom_Tags.dead,death_time]]        

class MissingTrajectoryMakerError(BaseException):
    pass
    
class SymptomsTrajectory(Symptoms):
    def __init__(self, health_index=0.,trajectory_maker = None, patient = None):
        super().__init__(health_index=health_index)
        if trajectory_maker==None:
            raise MissingTrajectoryMakerError(
                f"symptomstrajectory instantiated without trajectory_maker"
            )
        self.trajectory = self.make_trajectory(trajectory_maker, patient)
        
    def make_trajectory(self,trajectory_maker,patient):
        maxtag = self.max_tag(self.max_severity)
        return trajectory_maker[maxtag,patient]
        
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


