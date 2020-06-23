from abc import ABC, abstractmethod
from typing import List, Tuple

import yaml
from scipy import stats

from june import paths
from june.infection.symptom_tag import SymptomTag

default_config_path = paths.configs_path / "defaults/symptoms/trajectories.yaml"


class CompletionTime(ABC):
    @abstractmethod
    def __call__(self) -> float:
        """
        Compute the time a given stage should take to complete
        """

    @staticmethod
    def class_for_type(type_string: str) -> type:
        """
        Get a CompletionTime class from a string in configuration

        Parameters
        ----------
        type_string
            The type of CompletionTime
            e.g. constant/exponential/beta

        Returns
        -------
        The corresponding class

        Raises
        ------
        AssertionError
            If the type string is not recognised
        """
        if type_string == "constant":
            return ConstantCompletionTime
        if type_string == "exponential":
            return ExponentialCompletionTime
        if type_string == "beta":
            return BetaCompletionTime
        if type_string == "lognormal":
            return LognormalCompletionTime
        raise AssertionError(
            f"Unrecognised variation type {type_string}"
        )

    @classmethod
    def from_dict(cls, variation_type_dict):
        type_string = variation_type_dict.pop(
            "type"
        )
        return CompletionTime.class_for_type(
            type_string
        )(**variation_type_dict)


class ConstantCompletionTime(CompletionTime):
    def __init__(self, value: float):
        self.value = value

    def __call__(self):
        return self.value


class DistributionCompletionTime(CompletionTime, ABC):
    def __init__(
            self,
            distribution
    ):
        self.distribution = distribution

    def __call__(self):
        return self.distribution.rvs()


class ExponentialCompletionTime(DistributionCompletionTime):
    def __init__(self, loc: float, scale):
        super().__init__(
            stats.expon(
                loc=loc,
                scale=scale
            )
        )
        self.loc = loc
        self.scale = scale


class BetaCompletionTime(DistributionCompletionTime):
    def __init__(
            self,
            a,
            b,
            loc=0.0,
            scale=1.0
    ):
        super().__init__(
            stats.beta(
                a,
                b,
                loc=loc,
                scale=scale
            )
        )
        self.a = a
        self.b = b
        self.loc = loc
        self.scale = scale

class LognormalCompletionTime(DistributionCompletionTime):
    def __init__(
            self,
            s,
            loc=0.0,
            scale=1.0
    ):
        super().__init__(
            stats.lognorm(
                s,
                loc=loc,
                scale=scale
            )
        )
        self.s = s
        self.loc = loc
        self.scale = scale





class Stage:
    def __init__(
            self,
            *,
            symptoms_tag: SymptomTag,
            completion_time: CompletionTime = ConstantCompletionTime
    ):
        """
        A stage on an illness,

        Parameters
        ----------
        symptoms_tag
            What symptoms does the person have at this stage?
        completion_time
            Function that returns value for how long this stage takes
            to complete.
        """
        self.symptoms_tag = symptoms_tag
        self.completion_time = completion_time

    @classmethod
    def from_dict(cls, stage_dict):
        completion_time = CompletionTime.from_dict(
            stage_dict["completion_time"]
        )
        symptom_tag = SymptomTag.from_string(
            stage_dict["symptom_tag"]
        )
        return Stage(
            symptoms_tag=symptom_tag,
            completion_time=completion_time
        )


class TrajectoryMaker:
    def __init__(self, *stages):
        """
        Generate trajectories of a particular kind.

        This defines how a given person moves through a series of symptoms.

        Parameters
        ----------
        stages
            A list of stages through which the person progresses
        """
        self.stages = stages

    @property
    def _symptoms_tags(self):
        return [
            stage.symptoms_tag
            for stage in self.stages
        ]

    @property
    def most_severe_symptoms(self) -> SymptomTag:
        """
        The most severe symptoms experienced at any stage in this trajectory
        """
        return max(
            self._symptoms_tags
        )

    def generate_trajectory(self) -> List[
        Tuple[
            float,
            SymptomTag
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
            time = stage.completion_time()
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
        return TrajectoryMaker(
            *map(
                Stage.from_dict,
                trajectory_dict["stages"]
            ),
        )


class TrajectoryMakers:
    """
    The various trajectories should depend on external data, and may depend on age &
    gender of the patient.  This would lead to a table of tons of trajectories, with
    lots of mean values/deviations and an instruction on how to vary them.
    For this first simple implementation I will choose everything to be fixed (constant)

    The trajectories will count "backwards" with zero time being the moment of
    infection.
    """

    __instance = None
    __path = None

    def __init__(self, trajectories: List[TrajectoryMaker]):
        """
        Trajectories and their stages should be parsed from configuration. I've
        removed params for now as they weren't being used but it will be trivial
        to reintroduce them when we are ready for configurable trajectories.
        """
        self.trajectories = {
            trajectory.most_severe_symptoms: trajectory
            for trajectory in trajectories
        }

    @classmethod
    def from_file(cls, config_path: str = default_config_path) -> "TrajectoryMakers":
        """
        Currently this doesn't do what it says it does.

        By setting an instance on the class we can make the trajectory maker
        something like a singleton. However, if it were being loaded from
        configurations we'd need to be careful as this could give unexpected
        effects.
        """
        if cls.__instance is None or cls.__path != config_path:
            with open(config_path) as f:
                cls.__instance = TrajectoryMakers.from_list(
                    yaml.safe_load(f)["trajectories"]
                )
                cls.__path = config_path
        return cls.__instance

    def __getitem__(
            self,
            tag: SymptomTag
    ) -> List[Tuple[
        float,
        SymptomTag
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
    def from_list(cls, trajectory_dicts):
        return TrajectoryMakers(
            trajectories=list(map(
                TrajectoryMaker.from_dict,
                trajectory_dicts
            ))
        )
