import statistics
from pathlib import Path

import numpy as np

import june.infection.symptoms
from june.demography import person
from june.infection import Infection, InfectionSelector, TransmissionType
from june.infection import symptoms_trajectory as symtraj
from june.infection import transmission_xnexp as transxnexp
from june.infection.health_information import HealthInformation

path_pwd = Path(__file__)
dir_pwd = path_pwd.parent
constant_config = dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"


class TestInfection:
    def test__infect_person__gives_them_symptoms_and_transmission(self):
        selector = InfectionSelector.from_file()
        victim = person.Person(sex='f', age=26)
        victim.health_information = HealthInformation()
        selector.infect_person_at_time(person=victim, time=0.2)

        assert victim.health_information.infection.start_time == 0.2
        assert isinstance(victim.health_information.infection.symptoms,
                          june.infection.symptoms.Symptoms)
        # assert person.health_information.infection.symptoms.recovery_rate == 0.2
        assert isinstance(victim.health_information.infection.transmission,
                          transxnexp.TransmissionXNExp)

        # fixed value hard-wired in infection_selector
        assert victim.health_information.infection.transmission.incubation_time == 2.6
        assert (victim.health_information.infection.transmission.norm_time ==
                selector.transmission_norm_time)
        assert (victim.health_information.infection.transmission.N ==
                selector.transmission_N)
        assert (victim.health_information.infection.transmission.alpha ==
                selector.transmission_alpha)

    def test__update_to_time__calls_transmission_symptoms_methods(self, transmission,
                                                                  symptoms):
        infection = Infection(start_time=0.1,
                              transmission=transmission,
                              symptoms=symptoms)

        infection.update_at_time(time=20.0)
        assert infection.last_time_updated == 20.0
        assert infection.infection_probability == transmission.probability


class TestInfectionSelector:
    def test__defaults_when_no_filename_is_given(self):
        selector = InfectionSelector.from_file()
        assert selector.ttype == TransmissionType.xnexp
        assert selector.incubation_time == 2.6
        assert selector.transmission_N == 1.
        assert selector.transmission_alpha == 5.
        assert selector.transmission_median == 1.

    def test__constant_filename(self):
        selector = InfectionSelector.from_file(config_filename=constant_config)
        assert selector.ttype == TransmissionType.constant
        assert selector.transmission_probability == 0.3

    def test__lognormal_in_maxprob(self):
        selector = InfectionSelector.from_file()
        dummy = person.Person(sex='f', age=26)
        maxprobs = []
        for i in range(100000):
            infection = selector.make_infection(time=0.1, person=dummy)
            maxprobs.append(infection.transmission.max_probability)
        np.testing.assert_allclose(statistics.mean(maxprobs), 1.13, rtol=0.02, atol=0.02)
        np.testing.assert_allclose(statistics.median(maxprobs), 1.00, rtol=0.02, atol=0.02)

    def test__xnexp_in_transmission(self):
        selector = InfectionSelector.from_file()
        dummy = person.Person(sex='f', age=26)
        infection = selector.make_infection(time=0., person=dummy)
        ratio = 1. / infection.transmission.max_probability
        max_t = (selector.transmission_N * selector.transmission_alpha *
                 selector.transmission_norm_time +
                 selector.incubation_time)
        infection.update_at_time(max_t)
        max_prob = ratio * infection.transmission.probability
        np.testing.assert_allclose(max_t, 7.60, rtol=0.02, atol=0.02)
        np.testing.assert_allclose(max_prob, 1.00, rtol=0.02, atol=0.02)
        """
        ts = []
        probs = []
        for i in range(500):
            infection.update_at_time(i*0.1)
            ts.append(i*0.1)
            probs.append(ratio*infection.transmission.probability)
        return ts, probs
        """


"""
if __name__=="__main__":
    import matplotlib.pyplot as plt
    tester   = TestInfectionSelector()
    tester.test__defaults_when_no_filename_is_given()
    tester.test__constant_filename()
   
    ts,probs = tester.test__xnexp_in_transmission()
    plt.plot(ts,probs)
    plt.grid()
    plt.show()
"""
