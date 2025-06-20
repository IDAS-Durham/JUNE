import yaml
from june import paths
from .health_index.health_index import HealthIndexGenerator
from .infection import Infection
from .infection import Covid19  
from .infection import Measles
from .infection import EVD68V
from .symptoms import Symptoms
from .trajectory_maker import TrajectoryMakers
from .transmission import TransmissionConstant, TransmissionGamma
from .transmission_xnexp import TransmissionXNExp
from .trajectory_maker import CompletionTime
from .disease_config import DiseaseConfig
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from june.demography import Person
    from .transmission import Transmission
    from june.epidemiology.infection.symptom_tag import SymptomTag

# Map disease names to infection classes
disease_to_infection_class = {
    "measles": Measles,
    "covid19": Covid19,
    "ev-d68-v": EVD68V
    # Add other diseases here as needed
}


class InfectionSelector:
    def __init__(
        self,
        disease_config: DiseaseConfig,
        infection_class: Optional[Infection] = None,
        trajectory_maker: Optional[TrajectoryMakers] = None,
        health_index_generator: Optional[HealthIndexGenerator] = None,
    ):
        """
        Selects the type of infection a person is given.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        infection_class : Infection, optional
            Infection class for the disease (e.g., Measles, Covid19).
        trajectory_maker : TrajectoryMakers, optional
            Object to manage symptom trajectories.
        health_index_generator : HealthIndexGenerator, optional
            Generator for health index based on infection outcomes.
        """
        self.disease_config = disease_config
        self.disease_name = disease_config.disease_name
        self.infection_class = infection_class or self._resolve_infection_class(self.disease_name)
        self.trajectory_maker = trajectory_maker or TrajectoryMakers.from_disease_config(self.disease_config)
        
        # Retrieve the rates file from DiseaseConfig
        self.health_index_generator = health_index_generator or HealthIndexGenerator.from_disease_config(
            disease_config=disease_config
        )
        
        self.transmission_type = None  # Will be initialized in `_load_transmission`
        self._load_transmission()


    @classmethod
    def from_disease_config(cls, disease_config: DiseaseConfig) -> "InfectionSelector":
        """
        Generate infection selector from default config file.

        Parameters
        ----------
        disease_name : str
            Name of the disease.

        Returns
        -------
        InfectionSelector
            An instance of the infection selector.
        """
        # Dynamically select the infection class based on the disease name
        infection_class = disease_to_infection_class.get(disease_config.disease_name.lower())

        # Initialize the InfectionSelector with all required components
        return cls(
            disease_config=disease_config,
            infection_class=infection_class,
            trajectory_maker=TrajectoryMakers.from_disease_config(disease_config),
            health_index_generator=HealthIndexGenerator.from_disease_config(
                disease_config=disease_config
            )
        )

    @staticmethod
    def _get_rates_file_path(disease_name: str) -> str:
        """
        Construct the rates file path for the given disease.

        Parameters
        ----------
        disease_name : str
            Name of the disease.

        Returns
        -------
        str
            Path to the rates file.
        """
        return paths.data_path / f"input/health_index/infection_outcome_rates_{disease_name.lower()}.csv"

    def _resolve_infection_class(self, disease_name: str) -> Infection:
        """
        Resolves the infection class based on the disease name.

        Parameters
        ----------
        disease_name : str
            Name of the disease.

        Returns
        -------
        Infection
            Infection class for the disease.
        """
        infection_class = disease_to_infection_class.get(disease_name.lower())
        if not infection_class:
            raise ValueError(f"No infection class defined for disease '{disease_name}'.")
        return infection_class

    def _load_transmission(self):
        """
        Load transmission config from the disease configuration.
        """
        transmission_config = self.disease_config.disease_yaml.get("disease", {}).get("transmission", {})
        self.transmission_type = transmission_config.get("type")

        if self.transmission_type == "xnexp":
            self._load_transmission_xnexp(transmission_config)
        elif self.transmission_type == "gamma":
            self._load_transmission_gamma(transmission_config)
        elif self.transmission_type == "constant":
            self._load_transmission_constant(transmission_config)
        else:
            raise NotImplementedError(f"Transmission type '{self.transmission_type}' is not implemented.")
        
    def infect_person_at_time(self, person: "Person", time: float):
        """
        Infects a person at a given time.

        Parameters
        ----------
        person : Person
            The person to be infected.
        time : float
            The time at which the infection occurs.
        """
        # Create and assign infection
        person.infection = self._make_infection(person, time)

        # Update immunity
        immunity_ids = person.infection.immunity_ids()
        person.immunity.add_immunity(immunity_ids)

    def _make_infection(self, person: "Person", time: float):
        """
        Generate symptoms and infectiousness of the infected person.

        Parameters
        ----------
        person : Person
            The person to be infected.
        time : float
            Time at which infection happens.

        Returns
        -------
        Infection
        """
        symptoms = self._select_symptoms(person)
        time_to_symptoms_onset = symptoms.time_exposed
        transmission = self._select_transmission(
            time_to_symptoms_onset=time_to_symptoms_onset,
            max_symptoms_tag=symptoms.max_tag,
        )
        return self.infection_class(
            transmission=transmission, symptoms=symptoms, start_time=time
        )

    def _select_symptoms(self, person: "Person") -> "Symptoms":
        """
        Select symptoms and their evolution for an infected person.

        Parameters
        ----------
        person : Person
            The person to be infected.

        Returns
        -------
        Symptoms
        """
        health_index = self.health_index_generator(person, infection_id=self.infection_id)
        symptoms = Symptoms(disease_config=self.disease_config, health_index=health_index)
        return symptoms
    
    @property
    def infection_id(self):
        """
        Retrieve the infection ID from the infection class.

        Returns
        -------
        str
        """
        return self.infection_class.infection_id()
    
    def _load_transmission_xnexp(self, transmission_config: dict):
        """
        Load parameters for transmission of type `xnexp`.

        Parameters
        ----------
        transmission_config : dict
            Dictionary containing configuration for the `xnexp` transmission type.
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
        Load parameters for transmission of type `gamma`.

        Parameters
        ----------
        transmission_config : dict
            Dictionary containing configuration for the `gamma` transmission type.
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
        Load parameters for transmission of type `constant`.

        Parameters
        ----------
        transmission_config : dict
            Dictionary containing configuration for the `constant` transmission type.
        """
        self.probability = CompletionTime.from_dict(transmission_config["probability"])


    def _select_transmission(
        self, time_to_symptoms_onset: float, max_symptoms_tag: "SymptomTag"
    ) -> "Transmission":
        """
        Selects the transmission type specified by the user in the configuration,
        and links its parameters to the symptom onset for the person (incubation
        period).

        Parameters
        ----------
        time_to_symptoms_onset : float
            Time from infection to symptom onset for the person.
        max_symptoms_tag : SymptomTag
            The maximum severity of symptoms for the person.

        Returns
        -------
        Transmission
            A transmission object configured for the specified disease and parameters.
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
            raise NotImplementedError(f"Transmission type {self.transmission_type} is not implemented.")


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
            return {Covid19.infection_id(): InfectionSelector.from_disease_config()}
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
