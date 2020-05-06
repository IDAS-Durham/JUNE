from covid.infection import infection as infect
from covid.groups.people import person as per

class TestInfection:

    def test__infect_person__gives_them_symptoms_and_transmission(self, transmission, symptoms):

        infection = infect.Infection(start_time=0.1, transmission=transmission, symptoms=symptoms)

        person = per.Person()

        infection.infect_person_at_time(person=person, time=0.2)

        assert person.health_information.infection.start_time == 0.2
        assert person.health_information.infection.transmission.probability == transmission.probability
        assert person.health_information.infection.symptoms.recovery_rate == symptoms.recovery_rate

    def test__update_to_time__calls_transmission_symptoms_methods(self, transmission, symptoms):

        infection = infect.Infection(start_time=0.1, transmission=transmission, symptoms=symptoms)

        severity_before_update = infection.symptoms.severity

        infection.update_at_time(time=0.2)

        assert infection.last_time_updated == 0.2
        assert infection.symptoms.severity != severity_before_update
        assert infection.infection_probability == transmission.probability