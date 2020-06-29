import pytest

import june.infection.symptom_tag
from june.demography.person import Person
from june.infection import infection as infect, SymptomTag
from june.infection import symptoms as sym
from june.infection.trajectory_maker import (
    Stage, CompletionTime, ConstantCompletionTime, ExponentialCompletionTime,
    TrajectoryMaker,
    TrajectoryMakers,
    BetaCompletionTime
)


@pytest.fixture(
    name="constant_completion_dict"
)
def make_completion_time_dict():
    return {
        "type": "constant",
        "value": 1.0
    }


@pytest.fixture(
    name="stage_dict"
)
def make_stage_dict(
        constant_completion_dict
):
    return {
        "completion_time": constant_completion_dict,
        "symptom_tag": "healthy"
    }


@pytest.fixture(
    name="trajectory_dict"
)
def make_trajectory_dict(
        stage_dict
):
    return {
        "symptom_tag": "healthy",
        "stages": [
            stage_dict
        ]
    }


class TestCompletionTime:
    def test_constant_completion_time(self):
        completion_time = ConstantCompletionTime(
            value=1.0
        )
        assert completion_time() == 1.0

    def test_exponential_completion_time(self):
        completion_time = ExponentialCompletionTime(
            loc=1.0,
            scale=1.0
        )
        assert completion_time() >= 1.0

    def test_beta_completion_time(self):
        completion_time = BetaCompletionTime(
            1.0,
            1.0
        )
        assert 0.0 <= completion_time() <= 1.0


class TestParse:
    def test_symptoms_tag_for_string(self):
        assert SymptomTag.from_string("healthy") == SymptomTag.healthy
        with pytest.raises(
                AssertionError
        ):
            SymptomTag.from_string("nonsense")

    def test_parse_completion_time(self, constant_completion_dict):
        constant = CompletionTime.from_dict(constant_completion_dict)
        assert isinstance(
            constant,
            ConstantCompletionTime
        )

        exponential = CompletionTime.from_dict(
            {
                "type": "exponential",
                "loc": 1.0,
                "scale": 2.0
            }
        )
        assert isinstance(
            exponential,
            ExponentialCompletionTime
        )
        assert exponential.loc == 1.0
        assert exponential.scale == 2.0

    def test_parse_stage(self, stage_dict):
        stage = Stage.from_dict(stage_dict)

        assert isinstance(
            stage.completion_time,
            ConstantCompletionTime
        )
        assert stage.symptoms_tag == SymptomTag.healthy
        assert stage.completion_time.value == 1.0

    def test_parse_trajectory(self, trajectory_dict):
        trajectory = TrajectoryMaker.from_dict(
            trajectory_dict
        )
        assert trajectory.most_severe_symptoms == SymptomTag.healthy

        stage, = trajectory.stages
        assert stage.completion_time.value == 1.0

    def test_parse_trajectory_maker(self, trajectory_dict):
        trajectory_maker = TrajectoryMakers.from_list(
            [trajectory_dict]
        )
        assert trajectory_maker.trajectories[
                   SymptomTag.healthy
               ].stages[0].completion_time.value == 1.0


class TestTrajectoryMaker:
    def test__make__trajectories(self, trajectories):
        assert len(trajectories.trajectories) == 8
        influenza_trajectory = trajectories.trajectories[
            SymptomTag.influenza
        ]
        infected = influenza_trajectory.stages[0]
        assert infected.symptoms_tag == june.infection.symptom_tag.SymptomTag.exposed
        assert infected.completion_time.a == 2.29
        assert infected.completion_time.b == 19.05
        assert infected.completion_time.scale == 39.8

        recovered = influenza_trajectory.stages[-1]
        assert recovered.symptoms_tag == june.infection.symptom_tag.SymptomTag.recovered
        assert recovered.completion_time.value == 0.0

    def test_most_severe_symptoms(self, trajectories):
        for symptom_tag, trajectory in trajectories.trajectories.items():
            assert symptom_tag == trajectory.most_severe_symptoms


class TestSymptoms:
    def test__construct__trajectory__from__maxseverity(self, symptoms_trajectories):
        symptoms_trajectories.max_severity = 0.9
        symptoms_trajectories.update_trajectory()
        assert symptoms_trajectories.trajectory == [
            (0.0, june.infection.symptom_tag.SymptomTag.exposed),
            (pytest.approx(3.4, rel=0.5), june.infection.symptom_tag.SymptomTag.influenza),
            (pytest.approx(6.8, rel=0.5), june.infection.symptom_tag.SymptomTag.hospitalised),
            (pytest.approx(6.8, rel=0.5), june.infection.symptom_tag.SymptomTag.intensive_care),
            (pytest.approx(12, rel=0.5), june.infection.symptom_tag.SymptomTag.dead_icu)
        ]
        assert symptoms_trajectories.time_symptoms_onset() == symptoms_trajectories.trajectory[0][0]
        symptoms_trajectories.max_severity = 0.45
        symptoms_trajectories.update_trajectory()
        assert symptoms_trajectories.trajectory == [
            (0.0, june.infection.symptom_tag.SymptomTag.exposed),
            (pytest.approx(2, rel=0.5), june.infection.symptom_tag.SymptomTag.influenza),
            (pytest.approx(6.5, rel=0.5), june.infection.symptom_tag.SymptomTag.intensive_care),
            (pytest.approx(18.5, rel=0.5), june.infection.symptom_tag.SymptomTag.recovered)
        ]
        assert symptoms_trajectories.time_symptoms_onset() == symptoms_trajectories.trajectory[0][0]

    def test__symptoms_progression(self):
        selector = infect.InfectionSelector()
        dummy = Person(sex='f', age=65)
        infection = selector.make_infection(person=dummy, time=0.1)
        fixed_severity = 0.97
        infection.symptoms.max_severity = fixed_severity
        max_tag = infection.symptoms.max_tag()
        assert max_tag == june.infection.symptom_tag.SymptomTag.hospitalised
        infection.symptoms.trajectory = selector.trajectory_maker[max_tag]
        assert infection.symptoms.trajectory == [
            (0.0, june.infection.symptom_tag.SymptomTag.exposed),
            (pytest.approx(5, 2.5), june.infection.symptom_tag.SymptomTag.influenza),
            (pytest.approx(5, rel=5), june.infection.symptom_tag.SymptomTag.hospitalised),
            (pytest.approx(30, rel=5), june.infection.symptom_tag.SymptomTag.recovered)
        ]
        hospitalised_time = infection.symptoms.trajectory[2][0]

        infection.update_at_time(float(1.))
        assert infection.symptoms.tag == june.infection.symptom_tag.SymptomTag.exposed
        infection.update_at_time(float(1.))
        assert infection.symptoms.tag == june.infection.symptom_tag.SymptomTag.exposed
        infection.update_at_time(float(6.))
        assert infection.symptoms.tag == june.infection.symptom_tag.SymptomTag.influenza
        infection.update_at_time(hospitalised_time + 6)
        assert infection.symptoms.tag == june.infection.symptom_tag.SymptomTag.hospitalised
        infection.update_at_time(float(50.))
        assert infection.symptoms.tag == june.infection.symptom_tag.SymptomTag.recovered
