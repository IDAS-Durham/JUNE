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
    paths.configs_path / "defaults/infection/InfectionXNExp.yaml"
)


class SymptomsType(IntEnum):
    constant = (0,)
    gaussian = (1,)
    step = (2,)
    trajectories = 3


class InfectionSelector:
    def __init__(self, transmission_type: str, asymptomatic_ratio: float = 0.3):
        """
        Selects the type of infection a person is given

        Parameters
        ----------
        transmission_type:
            either constant or xnexp, controls the person's infectiousness profile over time
        asymptomatic_ratio:
            proportion of infected people that are asymptomatic
        """
        self.transmission_type = transmission_type
        self.trajectory_maker = TrajectoryMakers.from_file()
        self.health_index_generator = HealthIndexGenerator.from_file(
            asymptomatic_ratio=asymptomatic_ratio
        )

    @classmethod
    def from_file(
        cls,
        asymptomatic_ratio: float = 0.3,
        config_filename: str = default_config_filename,
    ) -> "InfectionSelector":
        """
        Generate infection selector from default config file
        
        Parameters
        ----------
        asymptomatic_ratio:
            proportion of infected people that are asymptomatic
        config_filename: 
            path to config file 
        """
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return InfectionSelector(config["transmission_type"], asymptomatic_ratio)

    def infect_person_at_time(self, person: "Person", time: float):
        """
        Infects a person at a given time

        Parameters
        ----------
        person:
            person that will be infected
        time:
            time at which infection happens
        """
        infection = self.make_infection(person, time)
        person.health_information = HealthInformation()
        person.health_information.set_infection(infection=infection)

    def make_infection(self, person: "Person", time: float):
        """
        Generates the symptoms and infectiousness of the person being infected

        Parameters
        ----------
        person:
            person that will be infected
        time:
            time at which infection happens
        """

        symptoms = self.select_symptoms(person)
        incubation_period = symptoms.time_exposed()
        transmission = self.select_transmission(person, incubation_period)
        return Infection(transmission=transmission, symptoms=symptoms, start_time=time)

    def select_transmission(self, person: "Person", incubation_period: float)->"Transmission":
        """
        Selects the transmission type specified by the user in the init, 
        and links its parameters to the symptom onset for the person (incubation
        period)

        Parameters
        ----------
        person:
            person that will be infected
        incubation_period:
            time of symptoms onset for person
        """
        if self.transmission_type == "xnexp":
            start_transmission = incubation_period - np.random.normal(2.0, 0.5)
            peak_position = (
                incubation_period - np.random.normal(0.7, 0.4) - start_transmission 
            )
            alpha = 1.5
            N = peak_position / alpha
            return TransmissionXNExp.from_file(
                start_transmission=start_transmission, N=N, alpha=alpha,
            )
        elif self.transmission_type == "constant":
            return TransmissionConstant.from_file()
        else:
            raise NotImplementedError("This transmission type has not been implemented")

    def select_symptoms(self, person: "Person")->"Symptoms":
        """
        Select the symptoms that a given person has, and how they will evolve
        in the future

        Parameters
        ----------
        person:
            person that will be infected
        """
        health_index = self.health_index_generator(person)
        return Symptoms(health_index=health_index)


class Infection:
    """
    The infection class combines the transmission (infectiousness profile) of the infected
    person, and their symptoms trajectory.
    """

    def __init__(self, transmission: "Transmission", symptoms: "Symptoms", start_time: float=-1):
        """
        Parameters
        ----------
        transmission:
            instance of the class that controls the infectiousness profile
        symptoms:
            instance of the class that controls the symptoms' evolution
        start_time:
            time at which the person is infected
        """
        self.start_time = start_time
        self.last_time_updated = start_time
        self.transmission = transmission
        self.symptoms = symptoms
        self.infection_probability = 0.0

    def update_at_time(self, time: float):
        """
        Updates symptoms and infectousness 

        Parameters
        ----------
        time:
            time elapsed from time of infection
        """
        if self.last_time_updated <= time:
            delta_time = time - self.start_time
            self.last_time_updated = time
            self.transmission.update_probability_from_delta_time(delta_time=delta_time)
            self.symptoms.update_severity_from_delta_time(delta_time=delta_time)
            self.infection_probability = self.transmission.probability

    @property
    def still_infected(self):
        return True
