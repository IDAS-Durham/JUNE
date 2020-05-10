import autofit as af
import pytest

from june.infection import infection as infect
from june.infection import symptoms as sym, transmission as trans
from june.demography import person as per

class TestInfection:

    def test__infect_person__gives_them_symptoms_and_transmission(self, transmission, symptoms):

        infection = infect.Infection(start_time=0.1, transmission=transmission, symptoms=symptoms)

        person = per.Person()

        epidemiology = af.CollectionPriorModel(
            symptoms=sym.SymptomsConstant,
            transmission=trans.TransmissionConstant
        )

        # PyAutoFit allows us to use Delta functions for the parameters, such that all Infections are given symptoms
        # and transmission with the same parameter values.

        epidemiology.symptoms.recovery_rate = 0.1
        epidemiology.transmission.probability = 0.2

        infection.infect_person_at_time(epidemiology=epidemiology, person=person, time=0.2)

        assert person.health_information.infection.start_time == 0.2

        assert isinstance(person.health_information.infection.symptoms, sym.SymptomsConstant)
        assert person.health_information.infection.symptoms.recovery_rate == 0.1
        assert person.health_information.infection.symptoms.health_index == person.health_index

        assert isinstance(person.health_information.infection.transmission, trans.TransmissionConstant)
        assert person.health_information.infection.transmission.probability == 0.2

        # Alternative, we can use Priors to draw these values from a distributioon.

        epidemiology.symptoms.recovery_rate = af.UniformPrior(lower_limit=0.499999, upper_limit=0.50001)
        epidemiology.transmission.probability = af.GaussianPrior(mean=0.3, sigma=0.000001)

        infection.infect_person_at_time(epidemiology=epidemiology, person=person, time=0.2)

        assert person.health_information.infection.start_time == 0.2

        assert isinstance(person.health_information.infection.symptoms, sym.SymptomsConstant)
        assert person.health_information.infection.symptoms.recovery_rate == pytest.approx(0.5, 1.0e-4)
        assert person.health_information.infection.symptoms.health_index == person.health_index

        assert isinstance(person.health_information.infection.transmission, trans.TransmissionConstant)
        assert person.health_information.infection.transmission.probability == pytest.approx(0.3, 1.0e-4)

    def test__update_to_time__calls_transmission_symptoms_methods(self, transmission, symptoms):

        infection = infect.Infection(start_time=0.1, transmission=transmission, symptoms=symptoms)

        severity_before_update = infection.symptoms.severity

        infection.update_at_time(time=0.2)

        assert infection.last_time_updated == 0.2
        assert infection.symptoms.severity != severity_before_update
        assert infection.infection_probability == transmission.probability
