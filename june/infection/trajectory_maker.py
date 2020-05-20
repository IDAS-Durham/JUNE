from enum import IntEnum

from june.infection.symptoms import SymptomTags


class VariationType(IntEnum):
    constant = 0,
    gaussian = 1,
    lognormal = 2


class Stage:
    def __init__(self):
        pass


class TrajectoryMaker:
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

    @classmethod
    def from_file(cls) -> "TrajectoryMaker":
        return cls(parameters=None)

    def __getitem__(self, tag):
        template = self.trajectories[tag[0]]
        cumulative = 0.
        trajectory = []
        for stage in template:
            time = stage[2]
            trajectory.append([cumulative, stage[1]])
            cumulative += time
        return trajectory

    def init_tables(self, parameters):
        self.incubation_info = self.FillIncubationTime(parameters)
        self.recovery_info = self.FillRecoveryInfo()
        for tag in SymptomTags:
            if tag == SymptomTags.asymptomatic:
                self.trajectories[tag] = self.FillAsymptomaticTrajectory(parameters)
            elif tag == SymptomTags.influenza:
                self.trajectories[tag] = self.FillInfluenzaLikeTrajectory(parameters)
            elif tag == SymptomTags.pneumonia:
                self.trajectories[tag] = self.FillPneumoniaTrajectory(parameters)
            elif tag == SymptomTags.hospitalised:
                self.trajectories[tag] = self.FillHospitalisedTrajectory(parameters)
            elif tag == SymptomTags.intensive_care:
                self.trajectories[tag] = self.FillIntensiveCareTrajectory(parameters)
            elif tag == SymptomTags.dead:
                self.trajectories[tag] = self.FillDeathTrajectory(parameters)

    def FillIncubationTime(self, parameters):
        incubation_time = 5.1  # parameters["incubation_time"] etc.
        return [VariationType.constant, SymptomTags.infected, incubation_time]

    def FillRecoveryInfo(self):
        return [VariationType.constant, SymptomTags.recovered, 0.0]

    def FillAsymptomaticTrajectory(self, parameters):
        recovery_time = 14.  # parameters["asymptomatic_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant, SymptomTags.asymptomatic, recovery_time],
                self.recovery_info]

    def FillInfluenzaLikeTrajectory(self, parameters):
        recovery_time = 20.  # parameters["influenza_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant, SymptomTags.influenza, recovery_time],
                self.recovery_info]

    def FillPneumoniaTrajectory(self, parameters):
        influenza_time = 5.  # parameters["pre_pneumonia_time"] etc.
        recovery_time = 20.  # parameters["pneumonia_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant, SymptomTags.influenza, recovery_time],
                [VariationType.constant, SymptomTags.pneumonia, recovery_time],
                self.recovery_info]

    def FillHospitalisedTrajectory(self, parameters):
        prehospital_time = 2.  # parameters["pre_hospital_time"] etc.
        recovery_time = 20.  # parameters["hospital_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant, SymptomTags.influenza, prehospital_time],
                [VariationType.constant, SymptomTags.hospitalised, recovery_time],
                self.recovery_info]

    def FillIntensiveCareTrajectory(self, parameters):
        prehospital_time = 2.  # parameters["pre_hospital_time"] etc.
        hospital_time = 2.  # parameters["hospital_time"] etc.
        ICU_time = 20.  # parameters["intensive_care_time"] etc.
        recovery_time = 20.  # parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant, SymptomTags.influenza, prehospital_time],
                [VariationType.constant, SymptomTags.hospitalised, prehospital_time],
                [VariationType.constant, SymptomTags.intensive_care, ICU_time],
                [VariationType.constant, SymptomTags.hospitalised, recovery_time],
                self.recovery_info]

    def FillDeathTrajectory(self, parameters):
        prehospital_time = 2.  # parameters["pre_hospital_time"] etc.
        hospital_time = 2.  # parameters["hospital_time"] etc.
        ICU_time = 10.  # parameters["intensive_care_time"] etc.
        death_time = 0.  # parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                [VariationType.constant, SymptomTags.influenza, prehospital_time],
                [VariationType.constant, SymptomTags.hospitalised, hospital_time],
                [VariationType.constant, SymptomTags.intensive_care, ICU_time],
                [VariationType.constant, SymptomTags.dead, death_time]]
