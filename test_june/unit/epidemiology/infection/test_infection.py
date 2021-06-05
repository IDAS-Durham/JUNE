import pytest
import statistics
import numpy as np
from pathlib import Path

from june import paths
import june.epidemiology.infection.symptoms
from june.demography import Person
from june.epidemiology.infection import symptoms_trajectory as symtraj
from june.epidemiology.infection import transmission_xnexp as transxnexp
from june.epidemiology.infection.infection_selector import (
    default_transmission_config_path,
)
from june.epidemiology.infection import (
    Infection,
    InfectionSelector,
    Covid19,
    B117,
    InfectionSelectors,
    transmission,
    SymptomTag,
)

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = (
    dir_pwd.parent.parent.parent
    / "configs/defaults/epidemiology/infection/InfectionConstant.yaml"
)


class MockInfection(Infection):
    pass


class MockHealthIndexGenerator:
    def __init__(self, desired_symptoms):
        self.index = {"asymptomatic": -1, "mild": 0, "severe": 1}[desired_symptoms]

    def __call__(self, person, infection_id):
        hi = np.ones(3)
        if self.index >= 0:
            hi[self.index] = 0
        return hi


def make_selector(
    desired_symptoms, transmission_config_path=default_transmission_config_path
):
    health_index_generator = MockHealthIndexGenerator(desired_symptoms)
    selector = InfectionSelector(
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
        selector = InfectionSelector(
            health_index_generator=MockHealthIndexGenerator("severe")
        )
        victim = Person.from_attributes(sex="f", age=26)
        selector.infect_person_at_time(person=victim, time=0.2)

        assert victim.infection.start_time == 0.2
        assert isinstance(
            victim.infection.symptoms,
            june.epidemiology.infection.symptoms.Symptoms,
        )
        assert isinstance(
            victim.infection.transmission,
            transmission.TransmissionGamma,
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
        selector = InfectionSelector()
        assert selector.transmission_type == "gamma"

    def test__constant_filename(self):
        selector = InfectionSelector(
            transmission_config_path=paths.configs_path
            / "defaults/epidemiology/infection/transmission/TransmissionConstant.yaml",
        )
        assert selector.transmission_type == "constant"

    def test__position_max_infectivity(self):
        dummy = Person.from_attributes(sex="f", age=26)
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
        dummy = Person.from_attributes(sex="f", age=26)
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
        health_index_generator = MockHealthIndexGenerator("severe")
        selector = InfectionSelector(
            transmission_config_path=paths.configs_path
            / "tests/transmission/test_transmission_lognormal.yaml",
            health_index_generator=health_index_generator,
        )
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )

        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability
        dummy = Person.from_attributes(sex="f", age=26)
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
            statistics.mean(norms),
            1.13,
            rtol=0.05,
        )
        np.testing.assert_allclose(
            statistics.median(norms),
            1.00,
            rtol=0.05,
        )
        np.testing.assert_allclose(
            statistics.median(maxprobs) / true_avg_peak_infectivity, 1.0, rtol=0.1
        )

    def test__infectivity_for_asymptomatic_carriers(self):
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )
        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability

        dummy = Person.from_attributes(sex="f", age=26)
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
            max_prob / true_avg_peak_infectivity,
            0.3,
            atol=0.1,
        )

    def test__infectivity_for_mild_carriers(self):
        avg_gamma = transmission.TransmissionGamma.from_file(
            config_path=paths.configs_path
            / "tests/transmission/test_transmission_constant.yaml"
        )
        avg_gamma.update_infection_probability(avg_gamma.time_at_maximum_infectivity)
        true_avg_peak_infectivity = avg_gamma.probability
        dummy = Person.from_attributes(sex="f", age=26)
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
            max_prob / true_avg_peak_infectivity,
            0.48,
            atol=0.1,
        )


class TestMultipleVirus:
    def test__infection_id_generation(self):
        infection1 = Covid19(transmission=None, symptoms=None)
        infection11 = Covid19(transmission=None, symptoms=None)
        infection2 = MockInfection(transmission=None, symptoms=None)
        infection22 = MockInfection(transmission=None, symptoms=None)
        assert type(infection1.infection_id()) == int
        assert infection1.infection_id() > 0
        assert infection1.infection_id() == infection11.infection_id()
        assert infection2.infection_id() == infection22.infection_id()
        assert infection1.infection_id() != infection2.infection_id()

    def test__multiple_virus(self):
        health_index_generator = MockHealthIndexGenerator("asymptomatic")
        selector1 = InfectionSelector(
            health_index_generator=health_index_generator,
            transmission_config_path=default_transmission_config_path,
        )
        p = Person.from_attributes(sex="f", age=26)
        infection = selector1._make_infection(person=p, time=0)
        assert isinstance(infection, Covid19)
        selector2 = InfectionSelector(
            infection_class=MockInfection,
            health_index_generator=health_index_generator,
            transmission_config_path=default_transmission_config_path,
        )
        infection = selector2._make_infection(person=p, time=0)
        assert isinstance(infection, MockInfection)
        infection_selectors = InfectionSelectors([selector1, selector2])
        assert set(infection_selectors.infection_id_to_selector.values()) == set(
            [selector1, selector2]
        )

    def test__immunity_multiple_virus(self):
        selector = InfectionSelector.from_file()
        person = Person.from_attributes()
        selector.infect_person_at_time(person, 0.0)
        assert person.immunity.is_immune(Covid19.infection_id())
        assert person.immunity.is_immune(B117.infection_id())
        assert person.infected
