import statistics
from pathlib import Path

import numpy as np

import june.infection.symptoms
from june.demography import person
from june.infection import Infection, InfectionSelector
from june.infection import symptoms_trajectory as symtraj
from june.infection import transmission
from june.infection import transmission_xnexp as transxnexp
from june.infection.health_information import HealthInformation
from june.infection.symptom_tag import SymptomTag
from june import paths

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"
)


def infect_person(person, selector, max_symptom_tag="mild"):
    infection = selector.make_infection(person, 0.0)
    infection.symptoms = june.infection.symptoms.Symptoms(
        health_index=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    )
    if max_symptom_tag == "asymptomatic":
        infection.symptoms.max_severity = 0.05
    elif max_symptom_tag == "mild":
        infection.symptoms.max_severity = 0.15
    elif max_symptom_tag == "severe":
        infection.symptoms.max_severity = 0.25
    infection.transmission = selector.select_transmission(
        person,
        time_to_symptoms_onset=infection.symptoms.time_exposed(),
        max_symptoms_tag=infection.symptoms.max_tag(),
    )
    return infection


class TestInfection:
    def test__infect_person__gives_them_symptoms_and_transmission(self):
        selector = InfectionSelector.from_file()
        victim = person.Person(sex="f", age=26)
        victim.health_information = HealthInformation()
        selector.infect_person_at_time(person=victim, time=0.2)

        assert victim.health_information.infection.start_time == 0.2
        assert isinstance(
            victim.health_information.infection.symptoms,
            june.infection.symptoms.Symptoms,
        )
        assert isinstance(
            victim.health_information.infection.transmission,
            transmission.TransmissionGamma,
        )

    def test__update_to_time__calls_transmission_symptoms_methods(
        self, transmission, symptoms
    ):
        infection = Infection(
            start_time=0.1, transmission=transmission, symptoms=symptoms
        )

        infection.update_at_time(time=20.0)
        assert infection.last_time_updated == 20.0
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

    def test__lognormal_in_maxprob(self):
        selector = InfectionSelector.from_file()
        dummy = person.Person(sex="f", age=26)
        maxprobs = []
        for i in range(1_000):
            infection = selector.make_infection(time=0.1, person=dummy)
            maxprobs.append(infection.transmission.max_infectiousness)
        np.testing.assert_allclose(
            statistics.mean(maxprobs), 1.13, rtol=0.02, atol=0.02
        )
        np.testing.assert_allclose(
            statistics.median(maxprobs), 1.00, rtol=0.02, atol=0.02
        )

    def test__xnexp_in_transmission(self):
        selector = InfectionSelector.from_file()
        dummy = person.Person(sex="f", age=26)
        infection = infect_person(
            person=dummy, selector=selector, max_symptom_tag="severe"
        )
        ratio = 1.0 / infection.transmission.max_infectiousness
        max_t = (
            infection.transmission.shape - 1
        ) * infection.transmission.scale + infection.transmission.shift
        infection.update_at_time(max_t)
        max_prob = ratio * infection.transmission.probability

        np.testing.assert_allclose(max_prob, 1.00, rtol=0.02, atol=0.02)

    def test__xnexp_in_asymptomatic_transmission(self):
        selector = InfectionSelector.from_file()
        dummy = person.Person(sex="f", age=26)
        infection = infect_person(
            person=dummy, selector=selector, max_symptom_tag="asymptomatic"
        )
        ratio = 1.0 / infection.transmission.max_infectiousness
        max_t = (
            infection.transmission.shape - 1
        ) * infection.transmission.scale + infection.transmission.shift
        infection.update_at_time(max_t)
        max_prob = ratio * infection.transmission.probability
        np.testing.assert_allclose(max_prob, 0.29, rtol=0.02, atol=0.02)

    def test__xnexp_in_mild_transmission(self):
        selector = InfectionSelector.from_file()
        dummy = person.Person(sex="f", age=26)
        infection = infect_person(
            person=dummy, selector=selector, max_symptom_tag="mild"
        )
        ratio = 1.0 / infection.transmission.max_infectiousness
        max_t = (
            infection.transmission.shape - 1
        ) * infection.transmission.scale + infection.transmission.shift
        infection.update_at_time(max_t)
        max_prob = ratio * infection.transmission.probability
        np.testing.assert_allclose(max_prob, 0.48, rtol=0.02, atol=0.02)
