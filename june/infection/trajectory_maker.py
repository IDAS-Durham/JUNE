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


class Trajectory:
    def __init__(self, *stages):
        self.trajectory = list()
        cumulative = 0.
        for stage in stages:
            time = stage.time
            self.trajectory.append([
                cumulative,
                stage.symptoms_tag
            ])
            cumulative += time

    def __iter__(self):
        return iter(self.trajectory)


class TrajectoryMaker:
    """
    The various trajectories should depend on external data, and may depend on age &
    gender of the patient.  This would lead to a table of tons of trajectories, with
    lots of mean values/deviations and an instruction on how to vary them.
    For this first simple implementation I will choose everything to be fixed (constant)

    The trajectories will count "backwards" with zero time being the moment of
    infection.
    """

    __instance = None

    def __init__(self):
        self.incubation_info = Stage(
            symptoms_tag=SymptomTags.infected,
            completion_time=5.1
        )
        self.recovery_info = Stage(
            symptoms_tag=SymptomTags.recovered,
            completion_time=0.0
        )
        self.trajectories = {
            SymptomTags.asymptomatic: Trajectory(
                self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.asymptomatic,
                    completion_time=14.
                ),
                self.recovery_info
            ),
            SymptomTags.influenza: Trajectory(
                self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=20.
                ),
                self.recovery_info
            ),
            SymptomTags.pneumonia: Trajectory(
                self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=5.
                ),
                Stage(
                    symptoms_tag=SymptomTags.pneumonia,
                    completion_time=20.
                ),
                self.recovery_info
            ),
            SymptomTags.hospitalised: Trajectory(
                self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=2.
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=20.
                ),
                self.recovery_info
            ),
            SymptomTags.intensive_care: Trajectory(
                self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=2.
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=2.
                ),
                Stage(
                    symptoms_tag=SymptomTags.intensive_care,
                    completion_time=20.
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=20.
                ),
                self.recovery_info
            ),
            SymptomTags.dead: Trajectory(
                self.incubation_info,
                Stage(
                    symptoms_tag=SymptomTags.influenza,
                    completion_time=2.
                ),
                Stage(
                    symptoms_tag=SymptomTags.hospitalised,
                    completion_time=2.
                ),
                Stage(
                    symptoms_tag=SymptomTags.intensive_care,
                    completion_time=10.
                ),
                Stage(
                    symptoms_tag=SymptomTags.dead,
                    completion_time=0.
                )
            )
        }

    @classmethod
    def from_file(cls) -> "TrajectoryMaker":
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __getitem__(self, tag):
        return self.trajectories[tag]
