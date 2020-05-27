from abc import ABC, abstractmethod
from typing import List, Tuple

from june.infection.symptoms import SymptomTags


class VariationType(ABC):
    @staticmethod
    @abstractmethod
    def time_for_stage(stage: "Stage") -> float:
        """
        Compute the time a given stage should take to complete

        Currently only ConstantVariationType is implemented. Other
        VariationTypes should extend this class.
        """

    @staticmethod
    def class_for_type(type_string):
        if type_string == "constant":
            return ConstantVariationType
        if type_string == "exponential":
            return ExponentialVariationType
        raise AssertionError(
            f"Unrecognised variation type {type_string}"
        )

    @classmethod
    def from_dict(cls, variation_type_dict):
        type_string = variation_type_dict.pop(
            "type"
        )
        return VariationType.class_for_type(
            type_string
        )(**variation_type_dict)


class ConstantVariationType(VariationType):
    @staticmethod
    def time_for_stage(stage):
        return stage.completion_time


class ExponentialVariationType(VariationType):
    def __init__(self, loc: float, scale: float):
        self.loc = loc
        self.scale = scale

    @staticmethod
    def time_for_stage(stage: "Stage") -> float:
        raise NotImplementedError("ExponentialVariationType not implemented")


class Stage:
    def __init__(
            self,
            *,
            symptoms_tag: SymptomTags,
            completion_time: float,
            variation_type: VariationType = ConstantVariationType
    ):
        """
        A stage on an illness,

        Parameters
        ----------
        symptoms_tag
            What symptoms does the person have at this stage?
        completion_time
            How long does this stage take to complete?
        variation_type
            The type of variation applied to the time of this stage
        """
        self.variation_type = variation_type
        self.symptoms_tag = symptoms_tag
        self.completion_time = completion_time

    def __eq__(self, other):
        return all([
            self.symptoms_tag is other.symptoms_tag,
            self.completion_time == other.completion_time,
            self.variation_type is other.variation_type
        ])

    def generate_time(self) -> float:
        """
        How long does this stage take for a particular patient?
        """
        return self.variation_type.time_for_stage(
            self
        )

    @classmethod
    def from_dict(cls, stage_dict):
        variation_type = VariationType.from_dict(
            stage_dict["variation_type"]
        )
        symptom_tag = SymptomTags.from_string(
            stage_dict["symptom_tag"]
        )
        completion_time = stage_dict["completion_time"]
        return Stage(
            variation_type=variation_type,
            symptoms_tag=symptom_tag,
            completion_time=completion_time
        )


class Trajectory:
    def __init__(self, *stages, symptom_tag: SymptomTags = None):
        """
        Generate trajectories of a particular kind.

        This defines how a given person moves through a series of symptoms.

        Parameters
        ----------
        stages
            A list of stages through which the person progresses
        """
        self.stages = stages
        self.symptom_tag = symptom_tag

    def generate_trajectory(self) -> List[
        Tuple[
            float,
            SymptomTags
        ]
    ]:
        """
        Generate a trajectory for a person. This is a list of tuples
        describing what symptoms the person should display at a given
        time.
        """
        trajectory = list()
        cumulative = 0.
        for stage in self.stages:
            time = stage.generate_time()
            trajectory.append((
                cumulative,
                stage.symptoms_tag
            ))
            cumulative += time
        return trajectory

    @classmethod
    def from_dict(
            cls,
            trajectory_dict
    ):
        return Trajectory(
            *map(
                Stage.from_dict,
                trajectory_dict["stages"]
            ),
            symptom_tag=SymptomTags.from_string(
                trajectory_dict["symptom_tag"]
            )
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

    __instance = None

    def __init__(self, trajectories: List[Trajectory]):
        """
        Trajectories and their stages should be parsed from configuration. I've
        removed params for now as they weren't being used but it will be trivial
        to reintroduce them when we are ready for configurable trajectories.
        """
        self.trajectories = {
            trajectory.symptom_tag: trajectory
            for trajectory in trajectories
        }

    @classmethod
    def from_file(cls) -> "TrajectoryMaker":
        """
        Currently this doesn't do what it says it does.

        By setting an instance on the class we can make the trajectory maker
        something like a singleton. However, if it were being loaded from
        configurations we'd need to be careful as this could give unexpected
        effects.
        """
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __getitem__(
            self,
            tag: SymptomTags
    ) -> List[Tuple[
        float,
        SymptomTags
    ]]:
        """
        Generate a trajectory from a tag.

        It might be better to have this return the Trajectory class
        rather than generating the trajectory itself. I feel the getitem
        syntax disguises the fact that something new is being created.

        I've removed the person (patient) argument because it was not
        being used. It can be passed to the generate_trajectory class.

        Parameters
        ----------
        tag
            A tag describing the symptoms being experienced by a
            patient.

        Returns
        -------
        A list describing the symptoms experienced by the patient
        at given times.
        """
        return self.trajectories[tag].generate_trajectory()

    @classmethod
    def from_dict(cls, trajectory_maker_dict):
        return TrajectoryMaker(
            trajectories=list(map(
                Trajectory.from_dict,
                trajectory_maker_dict[
                    "trajectories"
                ]
            ))
        )
