from enum import IntEnum

import numpy as np
import yaml

from june import paths
from june.infection.health_index import HealthIndexGenerator
from june.infection.health_information import HealthInformation
from june.infection.symptoms import Symptoms
from june.infection.trajectory_maker import TrajectoryMakers
from june.infection.transmission import TransmissionConstant
from june.infection.transmission_xnexp import TransmissionXNExp

default_config_filename = (
        paths.configs_path
        / "defaults/infection/InfectionTrajectoriesXNExp.yaml"
)


class SymptomsType(IntEnum):
    constant = 0,
    gaussian = 1,
    step = 2,
    trajectories = 3


class InfectionSelector:
    def __init__(self, transmission_type: str, asymptomatic_ratio:float=0.3):
        self.transmission_type = transmission_type
        self.trajectory_maker = TrajectoryMakers.from_file()
        self.health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=asymptomatic_ratio)

    @classmethod
    def from_file(
            cls,
            asymptomatic_ratio:float =0.43,
            config_filename: str = default_config_filename,
    ) -> "InfectionSelector":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return InfectionSelector(config['transmission_type'], asymptomatic_ratio)

    def infect_person_at_time(self, person, time):
        infection = self.make_infection(person, time)
        person.health_information = HealthInformation()
        person.health_information.set_infection(infection=infection)

    def make_infection(self, person, time):
        symptoms = self.select_symptoms(person)
        incubation_period = symptoms.time_exposed()
        transmission = self.select_transmission(person, incubation_period)
        return Infection(transmission=transmission,
                         symptoms=symptoms,
                         start_time=time)

    def select_transmission(self, person, incubation_period):
        if self.transmission_type == 'xnexp': 
            start_transmission = incubation_period - np.random.normal(3., 1.)
            peak_position = incubation_period - np.random.normal(0.7,1.)  #- start_transmission
            alpha = 1.
            N = peak_position/alpha

            return TransmissionXNExp.from_file(
                                     start_transmission=start_transmission,
                                     N=N,
                                     alpha=alpha,
                                     )
        elif self.transmission_type ==  'constant':
            return TransmissionConstant.from_file()
        else:
            raise NotImplementedError('This transmission type has not been implemented')

    def select_symptoms(self, person):
        health_index = self.health_index_generator(person)
        return Symptoms(health_index=health_index)


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
        self.start_time = start_time
        self.last_time_updated = start_time
        self.transmission = transmission
        self.symptoms = symptoms
        self.infection_probability = 0.0

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
    # self.symptoms.tag!=SymptomTags:recovered and
    # self.symptoms.tag!=SymptomTags:dead
