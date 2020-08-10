from enum import IntEnum

import numpy as np
import yaml

from june import paths
from june.infection.health_index import HealthIndexGenerator
from june.infection.health_information import HealthInformation
from june.infection.symptoms import Symptoms
from june.infection.trajectory_maker import TrajectoryMakers
from june.infection.transmission import TransmissionConstant, TransmissionGamma
from june.infection.transmission_xnexp import TransmissionXNExp
from june.infection.trajectory_maker import CompletionTime

default_transmission_config_path = (
    paths.configs_path / "defaults/transmission/nature.yaml"
)
default_trajectories_config_path = (
    paths.configs_path / "defaults/symptoms/trajectories.yaml"
)


class SymptomsType(IntEnum):
    constant = 0
    gaussian = 1
    step = 2
    trajectories = 3


class InfectionSelector:
    def __init__(
        self,
        transmission_config_path: str,
        trajectory_maker=TrajectoryMakers.from_file(default_trajectories_config_path),
        health_index_generator=HealthIndexGenerator.from_file(asymptomatic_ratio=0.3),
    ):
        """
        Selects the type of infection a person is given

        Parameters
        ----------
        transmission_config_path:
            path to transmission config file
        asymptomatic_ratio:
            proportion of infected people that are asymptomatic
        """
        self.transmission_config_path = transmission_config_path
        self.trajectory_maker = trajectory_maker
        self.health_index_generator = health_index_generator
        self.load_transmission()

    @classmethod
    def from_file(
        cls,
        transmission_config_path: str = default_transmission_config_path,
        trajectories_config_path: str = default_trajectories_config_path,
        health_index_generator: HealthIndexGenerator = HealthIndexGenerator.from_file(
            asymptomatic_ratio=0.3
        ),
    ) -> "InfectionSelector":
        """
        Generate infection selector from default config file
        
        Parameters
        ----------
        transmission_config_path:
            path to transmission config file
        trajectories_config_path:
            path to trajectories config file
        health_index_generator:
            health index generator
        """
        trajectory_maker = TrajectoryMakers.from_file(trajectories_config_path)
        return InfectionSelector(
            transmission_config_path=transmission_config_path,
            trajectory_maker=trajectory_maker,
            health_index_generator=health_index_generator,
        )

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
        person.susceptibility = 0.0
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
        time_to_symptoms_onset = symptoms.time_exposed()
        transmission = self.select_transmission(
            person=person,
            time_to_symptoms_onset=time_to_symptoms_onset,
            max_symptoms_tag=symptoms.max_tag(),
        )
        return Infection(transmission=transmission, symptoms=symptoms, start_time=time)

    def load_transmission(self):
        """
        Load transmission config file, and store objects that will generate random realisations
        """
        with open(self.transmission_config_path) as f:
            transmission_config = yaml.safe_load(f)
        self.transmission_type = transmission_config["type"]
        if self.transmission_type == "xnexp":
            self.load_transmission_xnexp(transmission_config)
        elif self.transmission_type == "gamma":
            self.load_transmission_gamma(transmission_config)
        elif self.transmission_type == "constant":
            self.load_transmission_constant(transmission_config)
        else:
            raise NotImplementedError("This transmission type has not been implemented")

    def load_transmission_xnexp(self, transmission_config: dict):
        """
        Given transmission config dictionary, load parameter generators from which
        transmission xnexp parameters will be sampled

        Parameters
        ----------
        transmission_config:
            dictionary of transmission config parameters
        """
        self.smearing_time_first_infectious = CompletionTime.from_dict(
            transmission_config["smearing_time_first_infectious"]
        )
        self.smearing_peak_position = CompletionTime.from_dict(
            transmission_config["smearing_peak_position"]
        )
        self.alpha = CompletionTime.from_dict(transmission_config["alpha"])
        self.max_probability = CompletionTime.from_dict(
            transmission_config["max_probability"]
        )
        self.norm_time = CompletionTime.from_dict(transmission_config["norm_time"])
        self.asymptomatic_infectious_factor = CompletionTime.from_dict(
            transmission_config["asymptomatic_infectious_factor"]
        )
        self.mild_infectious_factor = CompletionTime.from_dict(
            transmission_config["mild_infectious_factor"]
        )

    def load_transmission_gamma(self, transmission_config: dict):
        """
        Given transmission config dictionary, load parameter generators from which
        transmission gamma parameters will be sampled

        Parameters
        ----------
        transmission_config:
            dictionary of transmission config parameters
        """
        self.max_infectiousness = CompletionTime.from_dict(
            transmission_config["max_infectiousness"]
        )
        self.shape = CompletionTime.from_dict(transmission_config["shape"])
        self.rate = CompletionTime.from_dict(transmission_config["rate"])
        self.shift = CompletionTime.from_dict(transmission_config["shift"])
        self.asymptomatic_infectious_factor = CompletionTime.from_dict(
            transmission_config["asymptomatic_infectious_factor"]
        )
        self.mild_infectious_factor = CompletionTime.from_dict(
            transmission_config["mild_infectious_factor"]
        )

    def load_transmission_constant(self, transmission_config: dict):
        """
        Given transmission config dictionary, load parameter generators from which
        transmission constant parameters will be sampled

        Parameters
        ----------
        transmission_config:
            dictionary of transmission config parameters
        """
        self.probability = CompletionTime.from_dict(transmission_config["probability"])

    def select_transmission(
        self,
        person: "Person",
        time_to_symptoms_onset: float,
        max_symptoms_tag: "SymptomsTag",
    ) -> "Transmission":
        """
        Selects the transmission type specified by the user in the init, 
        and links its parameters to the symptom onset for the person (incubation
        period)

        Parameters
        ----------
        person:
            person that will be infected
        time_to_symptoms_onset:
            time of symptoms onset for person
        """
        if self.transmission_type == "xnexp":
            time_first_infectious = (
                self.smearing_time_first_infectious() + time_to_symptoms_onset
            )
            peak_position = (
                time_to_symptoms_onset
                - time_first_infectious
                + self.smearing_peak_position()
            )
            return TransmissionXNExp(
                max_probability=self.max_probability(),
                time_first_infectious=time_first_infectious,
                norm_time=self.norm_time(),
                n=peak_position / self.alpha(),
                alpha=self.alpha(),
                max_symptoms=max_symptoms_tag,
                asymptomatic_infectious_factor=self.asymptomatic_infectious_factor(),
                mild_infectious_factor=self.mild_infectious_factor(),
            )
        elif self.transmission_type == "gamma":
            return TransmissionGamma(
                max_infectiousness=self.max_infectiousness(),
                shape=self.shape(),
                rate=self.rate(),
                shift=self.shift() + time_to_symptoms_onset,
                max_symptoms=max_symptoms_tag,
                asymptomatic_infectious_factor=self.asymptomatic_infectious_factor(),
                mild_infectious_factor=self.mild_infectious_factor(),
            )
        elif self.transmission_type == "constant":
            return TransmissionConstant(probability=self.probability())
        else:
            raise NotImplementedError("This transmission type has not been implemented")

    def select_symptoms(self, person: "Person") -> "Symptoms":
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

    def __init__(
        self, transmission: "Transmission", symptoms: "Symptoms", start_time: float = -1
    ):
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
            time_from_infection = time - self.start_time
            self.last_time_updated = time
            self.transmission.update_probability_from_delta_time(
                time_from_infection=time_from_infection
            )
            self.symptoms.update_severity_from_delta_time(
                time_from_infection=time_from_infection
            )
            self.infection_probability = self.transmission.probability

    @property
    def still_infected(self):
        return True
