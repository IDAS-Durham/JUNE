import pytest

from june import paths
from june.epidemiology.infection import SymptomTag, InfectionSelector
from june.demography.person import Person
from june.epidemiology.infection.trajectory_maker import (
    Stage,
    CompletionTime,
    ConstantCompletionTime,
    ExponentialCompletionTime,
    TrajectoryMaker,
    TrajectoryMakers,
    BetaCompletionTime,
)

health_index = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]


@pytest.fixture(name="constant_completion_dict")
def make_completion_time_dict():
    return {"type": "constant", "value": 1.0}


@pytest.fixture(name="stage_dict")
def make_stage_dict(constant_completion_dict):
    return {"completion_time": constant_completion_dict, "symptom_tag": "healthy"}


@pytest.fixture(name="trajectory_dict")
def make_trajectory_dict(stage_dict):
    return {"symptom_tag": "healthy", "stages": [stage_dict]}


class TestCompletionTime:
    def test_constant_completion_time(self):
        completion_time = ConstantCompletionTime(value=1.0)
        assert completion_time() == 1.0

    def test_exponential_completion_time(self):
        completion_time = ExponentialCompletionTime(loc=1.0, scale=1.0)
        assert completion_time() >= 1.0

    def test_beta_completion_time(self):
        completion_time = BetaCompletionTime(1.0, 1.0)
        assert 0.0 <= completion_time() <= 1.0


class TestParse:
    def test_symptoms_tag_for_string(self):
        assert SymptomTag.from_string("healthy") == SymptomTag.healthy
        with pytest.raises(AssertionError):
            SymptomTag.from_string("nonsense")

    def test_parse_completion_time(self, constant_completion_dict):
        constant = CompletionTime.from_dict(constant_completion_dict)
        assert isinstance(constant, ConstantCompletionTime)

        exponential = CompletionTime.from_dict(
            {"type": "exponential", "loc": 1.0, "scale": 2.0}
        )
        assert isinstance(exponential, ExponentialCompletionTime)
        assert exponential.kwargs["loc"] == 1.0
        assert exponential.kwargs["scale"] == 2.0

    def test_parse_stage(self, stage_dict):
        stage = Stage.from_dict(stage_dict)

        assert isinstance(stage.completion_time, ConstantCompletionTime)
        assert stage.symptoms_tag == SymptomTag.healthy
        assert stage.completion_time.value == 1.0

    def test_parse_trajectory(self, trajectory_dict):
        trajectory = TrajectoryMaker.from_dict(trajectory_dict)
        assert trajectory.most_severe_symptoms == SymptomTag.healthy

        (stage,) = trajectory.stages
        assert stage.completion_time.value == 1.0

    def test_parse_trajectory_maker(self, trajectory_dict):
        trajectory_maker = TrajectoryMakers.from_list([trajectory_dict])
        assert (
            trajectory_maker.trajectories[SymptomTag.healthy]
            .stages[0]
            .completion_time.value
            == 1.0
        )


class TestTrajectoryMaker:
    def test__make__trajectories(self, trajectories):
        assert len(trajectories.trajectories) == 8
        mild_trajectory = trajectories.trajectories[SymptomTag.mild]
        infected = mild_trajectory.stages[0]
        assert infected.symptoms_tag == SymptomTag.exposed
        assert infected.completion_time.args[0] == 2.29
        assert infected.completion_time.args[1] == 19.05
        assert infected.completion_time.kwargs["scale"] == 39.8
        assert infected.completion_time.kwargs["loc"] == 0.39

        recovered = mild_trajectory.stages[-1]
        assert recovered.symptoms_tag == SymptomTag.recovered
        assert recovered.completion_time.value == 0.0

    def test_most_severe_symptoms(self, trajectories):
        for symptom_tag, trajectory in trajectories.trajectories.items():
            assert symptom_tag == trajectory.most_severe_symptoms


class TestSymptoms:
    def test__construct__trajectory__from__maxseverity(self, symptoms_trajectories):
        symptoms_trajectories.max_severity = 0.9
        symptoms_trajectories.trajectory = (
            symptoms_trajectories._make_symptom_trajectory(health_index)
        )
        symptoms_trajectories.time_of_symptoms_onset = (
            symptoms_trajectories._compute_time_from_infection_to_symptoms()
        )
        assert symptoms_trajectories.trajectory == [
            (0.0, SymptomTag.exposed),
            (pytest.approx(3.4, rel=0.5), SymptomTag.mild),
            (
                pytest.approx(6.8, rel=0.5),
                SymptomTag.hospitalised,
            ),
            (
                pytest.approx(6.8, rel=0.5),
                SymptomTag.intensive_care,
            ),
            (
                pytest.approx(20, rel=0.5),
                SymptomTag.dead_icu,
            ),
        ]
        assert (
            symptoms_trajectories.time_of_symptoms_onset
            == symptoms_trajectories.trajectory[1][0]
        )
        assert symptoms_trajectories.time_of_symptoms_onset > 0
        symptoms_trajectories.max_severity = 0.45
        symptoms_trajectories.trajectory = (
            symptoms_trajectories._make_symptom_trajectory(health_index)
        )
        symptoms_trajectories.time_of_symptoms_onset = (
            symptoms_trajectories._compute_time_from_infection_to_symptoms()
        )
        assert symptoms_trajectories.trajectory == [
            (0.0, SymptomTag.exposed),
            (pytest.approx(10, rel=0.5), SymptomTag.mild),
            (
                pytest.approx(13, rel=0.5),
                SymptomTag.hospitalised,
            ),
            (
                pytest.approx(15, rel=0.5),
                SymptomTag.intensive_care,
            ),
            (
                pytest.approx(20, rel=0.5),
                SymptomTag.hospitalised,
            ),
            (pytest.approx(34, rel=0.5), SymptomTag.mild),
            (
                pytest.approx(40, rel=0.5),
                SymptomTag.recovered,
            ),
        ]
        assert (
            symptoms_trajectories.time_of_symptoms_onset
            == symptoms_trajectories.trajectory[1][0]
        )
        assert symptoms_trajectories.time_of_symptoms_onset > 0
        symptoms_trajectories.max_severity = 0.05
        symptoms_trajectories.trajectory = (
            symptoms_trajectories._make_symptom_trajectory(health_index)
        )
        symptoms_trajectories.time_of_symptoms_onset = (
            symptoms_trajectories._compute_time_from_infection_to_symptoms()
        )
        assert symptoms_trajectories.time_of_symptoms_onset is None

    def test__symptoms_progression(self, health_index_generator):
        selector = InfectionSelector(
            health_index_generator=health_index_generator,
            transmission_config_path=paths.configs_path
            / "defaults/epidemiology/infection/transmission/TransmissionConstant.yaml",
        )
        dummy = Person(sex="f", age=65)
        health_index = selector.health_index_generator(dummy, 0)
        fixed_severity = 0.72
        infection = selector._make_infection(person=dummy, time=0.1)
        infection.symptoms.max_severity = fixed_severity
        infection.symptoms.trajectory = infection.symptoms._make_symptom_trajectory(
            health_index
        )
        max_tag = infection.symptoms.max_tag
        assert max_tag == SymptomTag.hospitalised
        assert infection.symptoms.trajectory == [
            (0.0, SymptomTag.exposed),
            (pytest.approx(5, 2.5), SymptomTag.mild),
            (
                pytest.approx(5, rel=5),
                SymptomTag.hospitalised,
            ),
            (pytest.approx(13, rel=5), SymptomTag.mild),
            (pytest.approx(30, rel=5), SymptomTag.recovered),
        ]
        hospitalised_time = infection.symptoms.trajectory[2][0]

        infection.update_symptoms_and_transmission(float(1.0))
        assert infection.symptoms.tag == SymptomTag.exposed
        infection.update_symptoms_and_transmission(float(1.0))
        assert infection.symptoms.tag == SymptomTag.exposed
        infection.update_symptoms_and_transmission(float(6.0))
        assert infection.symptoms.tag == SymptomTag.mild
        infection.update_symptoms_and_transmission(hospitalised_time + 8.0)
        assert infection.symptoms.tag == SymptomTag.hospitalised
        infection.update_symptoms_and_transmission(float(40.0))
        assert infection.symptoms.tag == SymptomTag.mild
        infection.update_symptoms_and_transmission(float(50.0))
        assert infection.symptoms.tag == SymptomTag.recovered
