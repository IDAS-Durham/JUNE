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


class TransmissionType(IntEnum):
    constant = 0,
    xnexp = 1


class InfectionSelector:
    def __init__(self, asymptomatic_ratio:float=0.43, config=None):
        transmission_type = "XNExp"
        if config is not None:
            if "transmission" in config and "type" in config["transmission"]:
                transmission_type = config["transmission"]["type"]
        self.trajectory_maker = TrajectoryMakers.from_file()
        self.init_transmission_parameters(transmission_type, config)
        self.health_index_generator = HealthIndexGenerator.from_file(asymptomatic_ratio=asymptomatic_ratio)

    def init_transmission_parameters(self, transmission_type, config):
        if transmission_type == "XNExp":
            self.ttype = TransmissionType.xnexp
            self.incubation_time = 2.6
            self.transmission_median = 1.
            self.transmission_sigma = 0.5
            self.transmission_norm_time = 1.
            self.transmission_N = 1.
            self.transmission_alpha = 5.
            if config is not None and "transmission" in config:
                if "incubation_time" in config["transmission"]:
                    self.incubation_time = config["transmission"]["incubation_time"]
                if "median" in config["transmission"]:
                    self.transmission_median = config["transmission"]["median"]
                if "sigma" in config["transmission"]:
                    self.transmission_sigma = config["transmission"]["sigma"]
                if "norm_time" in config["transmission"]:
                    self.transmission_norm_time = config["transmission"]["norm_time"]
                if "N" in config["transmission"]:
                    self.transmission_N = config["transmission"]["N"]
                if "alpha" in config["transmission"]:
                    self.transmission_alpha = config["transmission"]["alpha"]
            self.transmission_mu = np.log(self.transmission_median)
        else:
            self.ttype = TransmissionType.constant
            self.transmission_probability = 0.2
            if (config is not None and
                    "transmission" in config and "probability" in config["transmission"]):
                self.transmission_probability = config["transmission"]["probability"]

    @classmethod
    def from_file(
            cls,
            asymptomatic_ratio:float =0.43,
            config_filename: str = default_config_filename,
    ) -> "InfectionSelector":
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return InfectionSelector(asymptomatic_ratio,config)

    def infect_person_at_time(self, person, time):
        infection = self.make_infection(person, time)
        person.health_information = HealthInformation()
        person.health_information.set_infection(infection=infection)

    def make_infection(self, person, time):
        return Infection(transmission=self.select_transmission(person),
                         symptoms=self.select_symptoms(person),
                         start_time=time)

    def select_transmission(self, person):
        if self.ttype == TransmissionType.xnexp:
            maxprob = np.random.lognormal(self.transmission_mu,
                                          self.transmission_sigma)
            return TransmissionXNExp(max_probability=maxprob,
                                     incubation_time=self.incubation_time,
                                     norm_time=self.transmission_norm_time,
                                     N=self.transmission_N,
                                     alpha=self.transmission_alpha)
        else:
            return TransmissionConstant(probability=self.transmission_probability)

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
