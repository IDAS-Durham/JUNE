import numpy as np
import pytest

from june.demography.person import Person
from june.infection import infection as infect
from june.infection import symptoms as sym
from june.infection.health_index import HealthIndexGenerator
from june.infection.symptoms import SymptomsStep, SymptomTags
from june.infection.trajectory_maker import (
    Stage, CompletionTime, ConstantCompletionTime, ExponentialCompletionTime,
    Trajectory,
    TrajectoryMaker
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


class TestParse:
    def test_symptoms_tag_for_string(self):
        assert SymptomTags.from_string("healthy") == SymptomTags.healthy
        with pytest.raises(
                AssertionError
        ):
            SymptomTags.from_string("nonsense")

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
        assert stage.symptoms_tag == SymptomTags.healthy
        assert stage.completion_time.value == 1.0

    def test_parse_trajectory(self, trajectory_dict):
        trajectory = Trajectory.from_dict(
            trajectory_dict
        )
        assert trajectory.symptom_tag == SymptomTags.healthy

        stage, = trajectory.stages
        assert stage.completion_time.value == 1.0

    def test_parse_trajectory_maker(self, trajectory_dict):
        trajectory_maker = TrajectoryMaker.from_list(
            [trajectory_dict]
        )
        assert trajectory_maker.trajectories[
                   SymptomTags.healthy
               ].stages[0].completion_time.value == 1.0


class TestTrajectoryMaker:
    def test__make__trajectories(self, trajectories):
        assert len(trajectories.trajectories) == 6
        influenza_trajectory = trajectories.trajectories[
            SymptomTags.influenza
        ]
        infected = influenza_trajectory.stages[0]
        assert infected.symptoms_tag == sym.SymptomTags.infected
        assert infected.completion_time.value == 5.1

        recovered = influenza_trajectory.stages[-1]
        assert recovered.symptoms_tag == sym.SymptomTags.recovered
        assert recovered.completion_time.value == 0.0


class TestSymptomsTrajectory:
    def test__right_frequency_in_health_index(self):
        N_samples = 1000
        health_index = HealthIndexGenerator.from_file()(Person())
        frequencies = np.zeros(len(sym.SymptomTags))
        for i in range(N_samples):
            symptoms = SymptomsStep(health_index=health_index, time_offset=0.)
            symptoms.update_severity_from_delta_time(0.01)
            # check their symptoms matches the frequency in health index 
            if symptoms.tag != sym.SymptomTags.healthy:
                frequencies[symptoms.tag - 2] += 1
        np.testing.assert_allclose(frequencies[0] / N_samples, health_index[0], atol=0.05)
        np.testing.assert_allclose(frequencies[1] / N_samples, health_index[1] - health_index[0],
                                   atol=0.05)
        np.testing.assert_allclose(frequencies[2] / N_samples, health_index[2] - health_index[1],
                                   atol=0.05)
        np.testing.assert_allclose(frequencies[3] / N_samples, health_index[3] - health_index[2],
                                   atol=0.05)
        np.testing.assert_allclose(frequencies[4] / N_samples, health_index[4] - health_index[3],
                                   atol=0.05)

    def test__construct__trajectory__from__maxseverity(self, symptoms_trajectories):
        symptoms_trajectories.max_severity = 0.9
        symptoms_trajectories.update_trajectory()
        assert symptoms_trajectories.trajectory == [
            (0.0, sym.SymptomTags.infected),
            (5.1, sym.SymptomTags.influenza),
            (7.1, sym.SymptomTags.hospitalised),
            (9.1, sym.SymptomTags.intensive_care),
            (19.1, sym.SymptomTags.dead)
        ]
        symptoms_trajectories.max_severity = 0.45
        symptoms_trajectories.update_trajectory()
        assert symptoms_trajectories.trajectory == [
            (0.0, sym.SymptomTags.infected),
            (5.1, sym.SymptomTags.influenza),
            (7.1, sym.SymptomTags.hospitalised),
            (9.1, sym.SymptomTags.intensive_care),
            (29.1, sym.SymptomTags.hospitalised),
            (49.1, sym.SymptomTags.recovered)
        ]

    def test__symptoms__progression(self):
        selector = infect.InfectionSelector()
        dummy = Person(sex='m', age=65)
        infection = selector.make_infection(person=dummy, time=0.1)
        fixed_severity = 0.8
        infection.symptoms.max_severity = fixed_severity
        max_tag = infection.symptoms.max_tag()
        assert max_tag == sym.SymptomTags.hospitalised
        infection.symptoms.trajectory = selector.trajectory_maker[max_tag]
        assert infection.symptoms.trajectory == [
            (0.0, sym.SymptomTags.infected),
            (5.1, sym.SymptomTags.influenza),
            (7.1, sym.SymptomTags.hospitalised),
            (27.1, sym.SymptomTags.recovered)
        ]
        infection.update_at_time(float(1.))
        assert infection.symptoms.tag == sym.SymptomTags.infected
        infection.update_at_time(float(5.))
        assert infection.symptoms.tag == sym.SymptomTags.infected
        infection.update_at_time(float(6.))
        assert infection.symptoms.tag == sym.SymptomTags.influenza
        infection.update_at_time(float(10.))
        assert infection.symptoms.tag == sym.SymptomTags.hospitalised
        infection.update_at_time(float(20.))
        assert infection.symptoms.tag == sym.SymptomTags.hospitalised
        infection.update_at_time(float(30.))
        assert infection.symptoms.tag == sym.SymptomTags.recovered
