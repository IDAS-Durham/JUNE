import statistics
from pathlib import Path

import numpy as np
import pytest
import june.infection.symptoms
from june.demography import person, Population
from june.infection import Infection, InfectionSelector
from june.infection.infection_selector import default_transmission_config_path
from june.infection import symptoms_trajectory as symtraj
from june.infection import transmission
from june.infection import transmission_xnexp as transxnexp
from june.infection.symptom_tag import SymptomTag
from june import paths

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
)
susceptibility_config = paths.configs_path / 'tests/test_susceptibility.yaml'


class MockHealthIndexGenerator:
    def __init__(self, desired_symptoms):
        self.index = {"asymptomatic": -1, "mild": 0, "severe": 1}[desired_symptoms]

    def __call__(self, person):
        hi = np.ones(3)
        if self.index >= 0:
            hi[self.index] = 0
        return hi


def make_selector(
    desired_symptoms, transmission_config_path=default_transmission_config_path
):
    health_index_generator = MockHealthIndexGenerator(desired_symptoms)
    selector = InfectionSelector.from_file(
        health_index_generator=health_index_generator,
        transmission_config_path=transmission_config_path,
    )
    return selector


def infect_person(
    person,
    max_symptom_tag="mild",
    transmission_config_path=default_transmission_config_path,
):
    selector = make_selector(
        max_symptom_tag, transmission_config_path=transmission_config_path
    )
    infection = selector._make_infection(person, 0.0)
    if max_symptom_tag == "asymptomatic":
        assert infection.max_tag == SymptomTag.asymptomatic
    elif max_symptom_tag == "mild":
        assert infection.max_tag == SymptomTag.mild
    elif max_symptom_tag == "severe":
        assert infection.max_tag == SymptomTag.severe
    return infection, selector


class TestInfection:
    def test__infect_person__gives_them_symptoms_and_transmission(self):
        selector = InfectionSelector.from_file()
        victim = person.Person(sex="f", age=26)
        selector.infect_person_at_time(person=victim, time=0.2)

        assert victim.infection.start_time == 0.2
        assert isinstance(victim.infection.symptoms, june.infection.symptoms.Symptoms,)
        assert isinstance(
            victim.infection.transmission, transmission.TransmissionGamma,
        )

    def test__update_to_time__calls_transmission_symptoms_methods(
        self, transmission, symptoms
    ):
        infection = Infection(
            start_time=0.1, transmission=transmission, symptoms=symptoms
        )

        infection.update_symptoms_and_transmission(time=20.0)
        assert infection.infection_probability == transmission.probability


class TestInfectionSelector:
    def test__defaults_when_no_filename_is_given(self):
        selector = InfectionSelector.from_file()
        assert selector.transmission_type == "gamma"

    def test__constant_filename(self):
        selector = InfectionSelector.from_file(
            transmission_config_path=paths.configs_path
            / "defaults/transmission/TransmissionConstant.yaml",
        )
        assert selector.transmission_type == "constant"

    def test__position_max_infectivity(self):
        dummy = person.Person.from_attributes(sex="f", age=26)
        infection, _ = infect_person(person=dummy, max_symptom_tag="severe")
        true_max_t = infection.transmission.time_at_maximum_infectivity
        infectivity = []
        time_steps = np.linspace(0.0, 30.0, 500)
        for time in time_steps:
            infection.transmission.update_infection_probability(
                time_from_infection=time
            )
            infectivity.append(infection.transmission.probability)
        max_t = time_steps[np.argmax(np.array(infectivity))]
        assert max_t == pytest.approx(true_max_t, rel=0.01)

    def test__avg_peak_value(self):
        dummy = person.Person.from_attributes(sex="f", age=26)
        infection, selector = infect_person(
            person=dummy,
            max_symptom_tag="severe",
            transmission_config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml",
        )
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )
        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability
        peak_infectivity = []
        for i in range(100):
            infection = selector._make_infection(time=0.1, person=dummy)
            max_t = infection.transmission.time_at_maximum_infectivity
            infection.transmission.update_infection_probability(
                time_from_infection=max_t
            )
            peak_infectivity.append(infection.transmission.probability)
        assert np.mean(peak_infectivity) == pytest.approx(
            true_avg_peak_infectivity, rel=0.05
        )

    def test__lognormal_in_maxprob(self):
        selector = InfectionSelector.from_file(
            transmission_config_path=paths.configs_path
            / "tests/transmission/test_transmission_lognormal.yaml"
        )
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )

        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability
        dummy = person.Person.from_attributes(sex="f", age=26)
        norms, maxprobs = [], []
        for i in range(1_000):
            infection = selector._make_infection(time=0.1, person=dummy)
            norms.append(infection.transmission.norm)
            max_t = infection.transmission.time_at_maximum_infectivity
            infection.transmission.update_infection_probability(
                time_from_infection=max_t
            )
            maxprobs.append(infection.transmission.probability)

        np.testing.assert_allclose(
            statistics.mean(norms), 1.13, rtol=0.05,
        )
        np.testing.assert_allclose(
            statistics.median(norms), 1.00, rtol=0.05,
        )
        np.testing.assert_allclose(
            statistics.median(maxprobs) / true_avg_peak_infectivity, 1.0, rtol=0.06
        )

    def test__infectivity_for_asymptomatic_carriers(self):
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )
        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability

        dummy = person.Person(sex="f", age=26)
        infection, selector = infect_person(
            person=dummy,
            max_symptom_tag="asymptomatic",
            transmission_config_path=paths.configs_path
            / "tests/transmission/test_transmission_symptoms.yaml",
        )
        max_t = infection.transmission.time_at_maximum_infectivity
        infection.update_symptoms_and_transmission(max_t)
        max_prob = infection.transmission.probability
        np.testing.assert_allclose(
            max_prob / true_avg_peak_infectivity, 0.3, atol=0.1,
        )

    def test__infectivity_for_mild_carriers(self):
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )
        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability
        dummy = person.Person(sex="f", age=26)
        infection, selector = infect_person(
            person=dummy,
            max_symptom_tag="mild",
            transmission_config_path=paths.configs_path
            / "tests/transmission/test_transmission_symptoms.yaml",
        )
        max_t = infection.transmission.time_at_maximum_infectivity
        infection.update_symptoms_and_transmission(max_t)
        max_prob = infection.transmission.probability
        np.testing.assert_allclose(
            max_prob / true_avg_peak_infectivity, 0.48, atol=0.1,
        )

    def test__setting_susceptibility(self):
        dummy_young = person.Person.from_attributes(sex="f", age=10)
        dummy_old = person.Person.from_attributes(sex="f", age=30)
        dummy_very_old = person.Person.from_attributes(sex="f", age=99)
        population = Population([dummy_young, dummy_old, dummy_very_old])
        selector = InfectionSelector.from_file(
                susceptibilities_by_age_config_path = susceptibility_config
        )
        assert dummy_young.susceptibility == 1.
        selector.set_susceptibilities_by_age(population=population)
        assert dummy_young.susceptibility == 0.5
        assert dummy_old.susceptibility == 0.7
        assert dummy_very_old.susceptibility == 1.
        selector.infect_person_at_time(person=dummy_young, time=0.) 
        assert dummy_young.susceptibility == 0.


