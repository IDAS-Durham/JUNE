import numpy as np
from enum import IntEnum
import random
import sys
import autofit as af
from june.infection.symptoms            import SymptomsConstant
from june.infection.transmission        import TransmissionConstant
from june.infection.symptoms_trajectory import SymptomsTrajectory
from june.infection.transmission_xnexp  import TransmissionXNExp
from june.infection.trajectory_maker    import TrajectoryMaker 
from june.infection.health_index        import HealthIndexGenerator

class SymptomsType(IntEnum):
    constant     = 0,
    gaussian     = 1,
    step         = 2,
    trajectories = 3

class TransmissionType(IntEnum):
    constant = 0,
    xnexp    = 1

class InfectionSelector:
    def __init__(self,
                 transmission_type = "XNExp",
                 symptoms_type     = "Trajectories",
                 config = None
    ):
        self.health_index_generator = HealthIndexGenerator.from_file()
        self.init_parameters(transmission_type,symptoms_type)
        
    @classmethod
    def from_file(cls) -> "InfectionSelector":
        return cls(transmission_type = transmission_type,
                   symptoms_type     = symptoms_type,
                   config            = None)

        
    def init_parameters(self,transmission_type,symptoms_type):
        if symptoms_type=="Trajectories":
            self.trajectory_maker = TrajectoryMaker.from_file()
            self.stype            = SymptomsType.trajectories
        else:
            self.recovery_rate    = 0.2
            self.stype            = SymptomsType.constant
        if transmission_type=="XNExp":
            self.ttype                  = TransmissionType.xnexp
            self.incubation_time        = 2.6
            self.transmission_median    = 1.
            self.transmission_mu        = np.log(self.transmission_median)
            self.transmission_sigma     = 0.5
            self.transmission_norm_time = 1.
            self.transmission_N         = 1.
            self.transmission_alpha     = 5.
        else:
            self.ttype                    = TransmissionType.constant
            self.transmission_probability = 0.3
        
    def make_infection(self, person, time):
        return Infection(transmission = self.select_transmission(person),
                         symptoms     = self.select_symptoms(person),
                         start_time   = time)

    def select_transmission(self, person):
        if self.ttype==TransmissionType.xnexp:
            maxprob = np.random.lognormal(self.transmission_mu,
                                          self.transmission_sigma)
            return TransmissionXNExp(max_probability = maxprob,
                                     incubation_time = self.incubation_time,
                                     norm_time  = self.transmission_norm_time,
                                     N          = self.transmission_N,
                                     alpha      = self.transmission_alpha)
        else:
            return TransmissionConstant(probability=self.transmission_probability)

    def select_symptoms(self, person):
        health_index = self.health_index_generator(person)
        if self.stype==SymptomsType.trajectories:
            symptoms = SymptomsTrajectory(health_index = health_index)
            symptoms.make_trajectory(trajectory_maker = self.trajectory_maker,
                                     patient          = person)
        elif self.stype==SymptomsType.constant:
            symptoms = SymptomsConstant(health_index  = health_index,
                                        recovery_rate = self.recovery_rate)
        return symptoms


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
    def infect_person_at_time(self, selector, person, time):
        """
        Infects someone by initializing an infection object using the epidemiology model.

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
        #infection = Infection(
        #    start_time=time,
        #    transmission=transmission,  # instance.transmission,
        #    symptoms=symptoms,          # instance.symptoms
        #)
        infection = selector.make_infection(person,time)
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
        return True
    #self.symptoms.tag!=SymptomTags:recovered and
    #self.symptoms.tag!=SymptomTags:dead
