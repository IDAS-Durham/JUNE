from abc import ABC, abstractmethod

from june.infection.symptoms import SymptomTags


class VariationType(ABC):
    @staticmethod
    @abstractmethod
    def time_for_stage(stage):
        pass


class ConstantVariationType(VariationType):
    @staticmethod
    def time_for_stage(stage):
        return stage.completion_time


class Stage:
    def __init__(
            self,
            *,
            symptoms_tag: SymptomTags,
            completion_time: float,
            variation_type: VariationType = ConstantVariationType
    ):
        self.variation_type = variation_type
        self.symptoms_tag = symptoms_tag
        self.completion_time = completion_time

    def __eq__(self, other):
        return all([
            self.symptoms_tag is other.symptoms_tag,
            self.completion_time == other.completion_time,
            self.variation_type is other.variation_type
        ])

    @property
    def time(self):
        return self.variation_type.time_for_stage(
            self
        )


class TrajectoryMaker:
    """
    The various trajectories should depend on external data, and may depend on age &
    gender of the patient.  This would lead to a table of tons of trajectories, with
    lots of mean values/deviations and an instruction on how to vary them.
    For this first simple implementation I will choose everything to be fixed (constant)

    The trajectories will count "backwards" with zero time being the moment of
    infection.
    """

    def __init__(self):
        self.incubation_info = Stage(
            symptoms_tag=SymptomTags.infected,
            completion_time=5.1
        )
        self.recovery_info = Stage(
            symptoms_tag=SymptomTags.recovered,
            completion_time=0.0
        )
        self.trajectories = {}
        for tag in SymptomTags:
            if tag == SymptomTags.asymptomatic:
                self.trajectories[tag] = self.FillAsymptomaticTrajectory()
            elif tag == SymptomTags.influenza:
                self.trajectories[tag] = self.FillInfluenzaLikeTrajectory()
            elif tag == SymptomTags.pneumonia:
                self.trajectories[tag] = self.FillPneumoniaTrajectory()
            elif tag == SymptomTags.hospitalised:
                self.trajectories[tag] = self.FillHospitalisedTrajectory()
            elif tag == SymptomTags.intensive_care:
                self.trajectories[tag] = self.FillIntensiveCareTrajectory()
            elif tag == SymptomTags.dead:
                self.trajectories[tag] = self.FillDeathTrajectory()

    @classmethod
    def from_file(cls) -> "TrajectoryMaker":
        return cls()

    def __getitem__(self, tag):
        template = self.trajectories[tag]
        cumulative = 0.
        trajectory = []
        for stage in template:
            time = stage.time
            trajectory.append([cumulative, stage.symptoms_tag])
            cumulative += time
        return trajectory

    def FillAsymptomaticTrajectory(self):
        recovery_time = 14.  # parameters["asymptomatic_recovery_time"] etc.
        return [self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.asymptomatic,
                    completion_time=recovery_time
                ),
                self.recovery_info]

    def FillInfluenzaLikeTrajectory(self):
        recovery_time = 20.  # parameters["influenza_recovery_time"] etc.
        return [self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=recovery_time
                ),
                self.recovery_info]

    def FillPneumoniaTrajectory(self):
        influenza_time = 5.  # parameters["pre_pneumonia_time"] etc.
        recovery_time = 20.  # parameters["pneumonia_recovery_time"] etc.
        return [self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=recovery_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.pneumonia,
                    completion_time=recovery_time
                ),
                self.recovery_info]

    def FillHospitalisedTrajectory(self):
        prehospital_time = 2.  # parameters["pre_hospital_time"] etc.
        recovery_time = 20.  # parameters["hospital_recovery_time"] etc.
        return [self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=prehospital_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=recovery_time
                ),
                self.recovery_info]

    def FillIntensiveCareTrajectory(self):
        prehospital_time = 2.  # parameters["pre_hospital_time"] etc.
        hospital_time = 2.  # parameters["hospital_time"] etc.
        ICU_time = 20.  # parameters["intensive_care_time"] etc.
        recovery_time = 20.  # parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=prehospital_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=prehospital_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.intensive_care,
                    completion_time=ICU_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=recovery_time
                ),
                self.recovery_info]

    def FillDeathTrajectory(self):
        prehospital_time = 2.  # parameters["pre_hospital_time"] etc.
        hospital_time = 2.  # parameters["hospital_time"] etc.
        ICU_time = 10.  # parameters["intensive_care_time"] etc.
        death_time = 0.  # parameters["ICU_recovery_time"] etc.
        return [self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=prehospital_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=hospital_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.intensive_care,
                    completion_time=ICU_time
                ),
                Stage(
                    symptoms_tag=SymptomTags.dead,
                    completion_time=death_time
                )]
