import autofit as af
from june.infection.symptoms import Symptoms
from june.infection.infection_selecotr import InfectionSelector

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

    def __init__(self, transmission, symptoms, start_time=-1):
        self.start_time            = start_time
        self.last_time_updated     = start_time
        self.transmission          = transmission
        self.symptoms              = symptoms
        self.infection_probability = 0.0

    # def infect_person_at_time(self, epidemiology : af.CollectionPriorModel, person, time):
    def infect_person_at_time(self, person, health_index_generator, time):
        """Infects someone by initializing an infection object using the epidemiology model.

        The epidemiology input uses a CollectionPriorModel of PyAutoFit, which has 
        associated with it a Symptoms class and Transmission class. Every parameter in 
        these classes has a distribution, such that when the new infection is created 
        new parameters its new Symptoms and Transmission instances are randomly from a
        distribution.

        For example the recovery_rate of the SymptomsConstant class have a uniform 
        distribution with lower and upper limits of 0.2 and 0.4. When the infection 
        takes place, a value between 0.2 and 0.4 is randomly drawn and used to set the 
        value for the new instance of the Symptoms class in the new infection.

        Arguments:
        - epidemiology (af.CollectionPriorModel) the epidemiology model used to generate 
          the new infections symptoms and transmission instances.
        - person (Person) has to be an instance of the Person class.
        - time (float) the time of infection.
        """

        # instance = epidemiology.random_instance()

        # TODO : This is hacky, whats the best way we can feed health information through
        # to symptoms. Can we move the
        # instance.symptoms.health_index = self.symptoms.health_index

        infection = Infection(
            start_time=time,
            transmission=self.transmission,  # instance.transmission,
            symptoms=symptoms,               # instance.symptoms
        )
        person.health_information.set_infection(infection=infection)

    def update_at_time(self, time):

        if self.last_time_updated <= time:
            delta_time = time - self.start_time
            self.last_time_updated = time
            self.transmission.update_probability_from_delta_time(delta_time=delta_time)
            self.symptoms.update_severity_from_delta_time(delta_time=delta_time)
            self.infection_probability = self.transmission.probability

    @property
    def still_infected(self):
        return (self.symptoms.tag!=SymptomTags:recovered and
                self.symptoms.tag!=SymptomTags:dead) 
