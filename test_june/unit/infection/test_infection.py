import autofit as af
import pytest
import numpy as np
import statistics

from june.infection.health_index import HealthIndexGenerator
from june.infection import infection as infect
from june.infection import symptoms as sym, transmission as trans
from june.infection import symptoms_trajectory as symtraj
from june.infection import transmission_xnexp as transxnexp
from june.demography import person

class Test_Infection:
    def test__infect_person__gives_them_symptoms_and_transmission(self):
        selector  = infect.InfectionSelector()
        dummy     = person.Person(sex='f', age=26)
        infection = selector.make_infection(time=0.1,person=dummy)
        victim    = person.Person(sex='f', age=26)
        infection.infect_person_at_time(selector=selector, person=victim, time=0.2)
        
        assert victim.health_information.infection.start_time == 0.2
        assert isinstance(victim.health_information.infection.symptoms,
                          symtraj.SymptomsTrajectory)
        #assert person.health_information.infection.symptoms.recovery_rate == 0.2
        assert isinstance(victim.health_information.infection.transmission,
                          transxnexp.TransmissionXNExp)
        
        # fixed value hard-wired in infection_selector
        assert victim.health_information.infection.transmission.incubation_time == 2.6
        assert victim.health_information.infection.transmission.norm_time       == 5.
        assert victim.health_information.infection.transmission.N               == 2.
        assert victim.health_information.infection.transmission.alpha           == 10.
        
    def test__update_to_time__calls_transmission_symptoms_methods(self,transmission,
                                                                  symptoms):
        infection = infect.Infection(start_time=0.1,
                                     transmission=transmission,
                                     symptoms=symptoms)
        
        severity_before_update = infection.symptoms.severity
        infection.update_at_time(time=0.2)
        assert infection.last_time_updated     == 0.2
        assert infection.symptoms.severity     != severity_before_update
        assert infection.infection_probability == transmission.probability

class Test_InfectionSelector:
    def test__lognormal_in_maxprob(self):
        selector  = infect.InfectionSelector()
        dummy     = person.Person(sex='f', age=26)
        maxprobs  = []
        for i in range(100000):
            infection = selector.make_infection(time=0.1,person=dummy)
            maxprobs.append(infection.transmission.max_probability)
        np.testing.assert_allclose(statistics.mean(maxprobs),   1.13, rtol=0.02, atol=0.02)
        np.testing.assert_allclose(statistics.median(maxprobs), 1.00, rtol=0.02, atol=0.02) 

    def test__xnexp_in_transmission(self):
        selector  = infect.InfectionSelector()
        dummy     = person.Person(sex='f', age=26)
        infection = selector.make_infection(time=0.,person=dummy)
        ratio     = 1./infection.transmission.max_probability
        max_t     = (selector.transmission_N * selector.transmission_alpha *
                     selector.transmission_norm_time +
                     selector.incubation_time)
        infection.update_at_time(max_t)
        max_prob  = ratio*infection.transmission.probability
        np.testing.assert_allclose(max_t,    7.60, rtol=0.02, atol=0.02) 
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
    tester   = Test_InfectionSelector()
    ts,probs = tester.test__xnexp_in_transmission()
    plt.plot(ts,probs)
    plt.grid()
    plt.show()
"""
