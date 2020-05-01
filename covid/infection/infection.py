import copy

class Infection:
    """
    The description of the infection, with two time dependent characteristics,
    which may vary by individual:
    - transmission probability, Ptransmission.
    - symptom severity, Severity
    Either of them will be a numer between 0 (low) and 1 (high, strong sypmotoms),
    and for both we will have some thresholds.
    Another important part for the infection is their begin, starttime, which must
    be given in the constructor.  Transmission probability and symptom severity
    can be added/modified a posteriori.
    """

    def __init__(self, start_time, transmission, symptoms):

        self.start_time = start_time
        self.last_time_updated = start_time
        self.transmission = transmission
        self.symptoms = symptoms

        self.infection_probability = 0.0

    def new_infection_at_time(self, time):

        # TODO : Currently assume transmission / symptoms parameters do not change between infections, will sort this
        # TODO : out in next refactor.

        return Infection(start_time=time, transmission=self.transmission, symptoms=self.symptoms)

    def infect_person_at_time(self, person, time):
        """Infects someone by initializing an infeciton object with the same type
        and parameters as the carrier's infection class.

        Arguments:
            person (Person) has to be an instance of the Person class.
        """

        infection = self.new_infection_at_time(time=time)
        person.health_information.set_infection(infection=infection)

    def symptom_tag(self, tagno):
        return self.symptoms.tag

    def update_at_time(self, time):

        if self.last_time_updated <= time:

            delta_time = time - self.start_time

            self.last_time_updated = time
            self.transmission.update_probability_from_delta_time(delta_time=delta_time)
            self.symptoms.update_severity_from_delta_time(delta_time=delta_time)
            self.infection_probability = self.transmission.probability

    @property
    def still_infected(self):

        # TODO : These can be determined using the instances of tranmsision, symptoms.

        #transmission_bool = (
        #    self.transmission != None
        #    and self.transmission.probability > self.threshold_transmission
        #)
        #symptoms_bool = (
        #    self.symptoms != None and self.symptoms.severity > self.threshold_symptoms
        #)
        #is_infected = transmission_bool or symptoms_bool
        return True

