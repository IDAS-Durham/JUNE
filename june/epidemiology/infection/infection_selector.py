from enum import IntEnum

import numpy as np
from itertools import count
import yaml

from june import paths
from .health_index.health_index import HealthIndexGenerator
from .health_index import Data2Rates
from . import Infection, Covid19
from .symptoms import Symptoms, SymptomTag
from .trajectory_maker import TrajectoryMakers
from .transmission import TransmissionConstant, TransmissionGamma
from .transmission_xnexp import TransmissionXNExp
from .trajectory_maker import CompletionTime

default_transmission_config_path = (
    paths.configs_path / "defaults/epidemiology/infection/transmission/covid19.yaml"
)
default_trajectories_config_path = (
    paths.configs_path / "defaults/epidemiology/infection/symptoms/trajectories.yaml"
)
default_rates_file = paths.data_path / "input/health_index/infection_outcome_rates.csv"


class InfectionSelector:
    def __init__(
        self,
        transmission_config_path: str = default_transmission_config_path,
        infection_class: Infection = Covid19,
        trajectory_maker=TrajectoryMakers.from_file(default_trajectories_config_path),
        health_index_generator: HealthIndexGenerator = None,
    ):
        """
        Selects the type of infection a person is given

        Parameters
        ----------
        transmission_config_path:
            path to transmission config file
        """
        self.infection_class = infection_class
        self.transmission_config_path = transmission_config_path
        self.trajectory_maker = trajectory_maker
        self.health_index_generator = health_index_generator
        self._load_transmission()

    @classmethod
    def from_file(
        cls,
        infection_class: Infection = Covid19,
        transmission_config_path: str = default_transmission_config_path,
        trajectories_config_path: str = default_trajectories_config_path,
        rates_file: str = default_rates_file,
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
        health_index_generator = HealthIndexGenerator.from_file(rates_file=rates_file)
        trajectory_maker = TrajectoryMakers.from_file(trajectories_config_path)
        return InfectionSelector(
            infection_class=infection_class,
            transmission_config_path=transmission_config_path,
            trajectory_maker=trajectory_maker,
            health_index_generator=health_index_generator,
        )

    @property
    def infection_id(self):
        return self.infection_class.infection_id()

    def infect_person_at_time(self, person: "Person", time: float):
        """
        Infects a person at a given time.

        Parameters
        ----------
        person:
            person that will be infected
        time:
            time at which infection happens
        """
        infection_id = self.infection_id
        person.infection = self._make_infection(person, time)
        person.immunity.add_immunity(person.infection.immunity_ids())

    def _make_infection(self, person: "Person", time: float):
        """
        Generates the symptoms and infectiousness of the person being infected

        Parameters
        ----------
        person:
            person that will be infected
        time:
            time at which infection happens
        """
        symptoms = self._select_symptoms(person)
        time_to_symptoms_onset = symptoms.time_exposed
        transmission = self._select_transmission(
            time_to_symptoms_onset=time_to_symptoms_onset,
            max_symptoms_tag=symptoms.max_tag.name,
        )
        return self.infection_class(
            transmission=transmission, symptoms=symptoms, start_time=time
        )

    def _load_transmission(self):
        """
        Load transmission config file, and store objects that will generate random realisations
        """
        with open(self.transmission_config_path) as f:
            transmission_config = yaml.safe_load(f)
        self.transmission_type = transmission_config["type"]
        if self.transmission_type == "xnexp":
            self._load_transmission_xnexp(transmission_config)
        elif self.transmission_type == "gamma":
            self._load_transmission_gamma(transmission_config)
        elif self.transmission_type == "constant":
            self._load_transmission_constant(transmission_config)
        else:
            raise NotImplementedError("This transmission type has not been implemented")

    def _load_transmission_xnexp(self, transmission_config: dict):
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

    def _load_transmission_gamma(self, transmission_config: dict):
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

    def _load_transmission_constant(self, transmission_config: dict):
        """
        Given transmission config dictionary, load parameter generators from which
        transmission constant parameters will be sampled

        Parameters
        ----------
        transmission_config:
            dictionary of transmission config parameters
        """
        self.probability = CompletionTime.from_dict(transmission_config["probability"])

    def _select_transmission(
        self,
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

    def _select_symptoms(self, person: "Person") -> "Symptoms":
        """
        Select the symptoms that a given person has, and how they will evolve
        in the future

        Parameters
        ----------
        person:
            person that will be infected
        infection_id:
            infection id
        """
        health_index = self.health_index_generator(person, infection_id=self.infection_id)
        return Symptoms(health_index=health_index)


class InfectionSelectors:
    def __init__(self, infection_selectors: list = None):
        self._infection_selectors = infection_selectors
        self.infection_id_to_selector = self.make_dict() 

    def make_dict(self):
        """
        Makes two dicts:
        infection_type_id -> infection_class (needed for easier MPI comms)
        infection_class -> infection_selector (needed to map infection to 
                            the class that creates infections)
        """
        if not self._infection_selectors:
            return {Covid19.infection_id(): InfectionSelector.from_file()}
        ret = {}
        for i, selector in enumerate(self._infection_selectors):
            ret[selector.infection_class.infection_id()] = selector
        return ret

    def infect_person_at_time(
        self, person: "Person", time: float, infection_id: int = Covid19.infection_id()
    ):
        """
        Infects a person at a given time with the given infection_class.

        Parameters
        ----------
        infection_class:
            type of infection to create
        person:
            person that will be infected
        time:
            time at which infection happens
        """
        selector = self.infection_id_to_selector[infection_id]
        selector.infect_person_at_time(person=person, time=time)

    def __iter__(self):
        return iter(self._infection_selectors)

    def __getitem__(self, item):
        return self._infection_selectors[item]
        
