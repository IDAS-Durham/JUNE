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
        self.transmission = transmission
        self.symptoms = symptoms

        self.last_time_updated = self.start_time  # testing
        self.infection_probability = 0.0

    def infect(self, person):
        """Infects someone by initializing an infeciton object with the same type
        and parameters as the carrier's infection class.

        Arguments:
            person (Person) has to be an instance of the Person class.
        """
        person.health_information.set_infection(infection=copy.deepcopy(self))

    def symptom_tag(self, tagno):
        return self.symptoms.tag

    @property
    def still_infected(self):
        raise NotImplementedError()

    def update_to_time(self, time):

        if self.last_time_updated <= time:

            self.last_time_updated = time
            self.transmission.update_probability_at_time(time=time)
            self.symptoms.update_severity_at_time(time=time)
            self.infection_probability = self.transmission.probability

class InfectionConstant(Infection):

    def __init__(self, start_time, transmission, symptoms, threshold_transmission=0.001, threshold_symptoms=0.001):

        super().__init__(start_time=start_time, transmission=transmission, symptoms=symptoms)

        self.threshold_tranmission = threshold_transmission
        self.threshold_symptoms = threshold_symptoms

    @property
    def still_infected(self):
        #transmission_bool = (
        #    self.transmission != None
        #    and self.transmission.probability > self.threshold_transmission
        #)
        #symptoms_bool = (
        #    self.symptoms != None and self.symptoms.severity > self.threshold_symptoms
        #)
        #is_infected = transmission_bool or symptoms_bool
        return True

