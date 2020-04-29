from covid.infection import infection as infect
from covid.groups.people import person as per

class TestInfection:

    def test__infect_person__gives_them_symptoms_and_transmission(self, transmission, symptoms):

        infection = infect.Infection(start_time=0.1, transmission=transmission, symptoms=symptoms)

        person = per.Person()

        infection.infect(person=person)

        assert person.health_information.infection.transmission.probability == transmission.probability
        assert person.health_information.infection.symptoms.recovery_rate == symptoms.recovery_rate

    def test__update_to_time__calls_transmission_symptoms_methods(self, transmission, symptoms):

        infection = infect.Infection(start_time=0.1, transmission=transmission, symptoms=symptoms)

        infection.update_to_time(time=1.0)

        assert infection.last_time_updated == 1.0
        assert infection.transmission.last_time_updated == 1.0
        assert infection.symptoms.last_time_updated == 1.0
        assert infection.infection_probability == transmission.probability