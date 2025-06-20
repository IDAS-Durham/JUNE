"""
This module handles the configuration of diseases for the epidemiology model.

Classes:
    - DiseaseConfig: Manages disease-specific configurations.
    - RatesManager: Handles infection outcome rates.
    - InteractionManager: Manages interaction-related configurations.
    - SymptomManager: Manages symptom-related configurations.
    - VaccinationManager: Manages vaccination-related configurations.
    - PolicyManager: Handles policy-related configurations.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import yaml
from june import paths

BASE_PATH = Path(__file__).parent.parent.parent

def load_yaml(file_path: Path) -> dict:
    """
    Utility function to load a YAML file.

    Parameters
    ----------
    file_path : Path
        The path to the YAML file.

    Returns
    -------
    dict
        The contents of the YAML file as a dictionary.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_nested_key(data: dict, keys: List[str], default=None):
    """
    Retrieve the value from a nested dictionary using a list of keys.

    This function iteratively traverses a dictionary using the provided list
    of keys to access nested values. If a key is missing at any level, the
    function returns the specified default value.

    Parameters
    ----------
    data : dict
        The dictionary to traverse.
    keys : List[str]
        A list of keys representing the path to the desired value.
    default : any, optional
        The value to return if any key in the path is missing (default is None).

    Returns
    -------
    any
        The value from the nested dictionary if all keys exist, otherwise the
        specified default value.
    """
    for key in keys:
        data = data.get(key, {})
    return data or default

class DiseaseConfig: # pylint: disable=too-few-public-methods
    """
    Manages the configuration of a specific disease.

    This class loads and parses disease-specific YAML configurations, 
    and initializes managers for rates, interactions, symptoms, 
    vaccinations, and policies.

    Attributes:
        disease_name (str): The name of the disease in lowercase.
        rates_manager (RatesManager): Manages infection outcome rates.
        interaction_manager (InteractionManager): Handles interactions.
        symptom_manager (SymptomManager): Manages symptoms.
        vaccination_manager (VaccinationManager): Manages vaccinations.
        policy_manager (PolicyManager): Handles policies.
    """
    def __init__(self, disease_name: str):
        self.disease_name = disease_name.lower()
        config_path = (
            paths.configs_path /
            f"defaults/epidemiology/infection/disease/{self.disease_name}.yaml"
            )
        # Load the main disease YAML
        with open(config_path, "r", encoding="utf-8") as f:
            self.disease_yaml = yaml.safe_load(f)

        self.rates_manager = RatesManager(self.disease_yaml, self.disease_name)
        self.interaction_manager = InteractionManager(self.disease_name)
        self.symptom_manager = SymptomManager(self.disease_yaml)
        self.vaccination_manager = VaccinationManager(self.disease_name)
        self.policy_manager = PolicyManager(self.disease_name)

class RatesManager:
    """
    Manages infection outcome rates for a specific disease.

    This class handles the loading and processing of infection outcome rates
    for a disease based on its configuration. It initializes rate structures,
    maps rates to symptom tags, and provides access to infection outcome rates.

    Attributes:
        rates_structure (dict): Structure to hold precomputed infection rates by parameter.
        rates_file (Path): Path to the CSV file containing infection outcome rates.
        rate_to_tag_mapping (dict): Mapping from rate names to symptom tags.
        symptom_tags (dict): Mapping of symptom tag names to their values.
        unrated_tags (list): Tags that are not associated with specific rates.
        infection_outcome_rates (list): List of infection outcome rates defined 
            in the configuration.
    """
    def __init__(self, disease_yaml: dict, disease_name: str):
        self.rates_file: Path = (
            paths.data_path /
            f"input/health_index/infection_outcome_rates_{disease_name.lower()}.csv"
        )
        self.rate_to_tag_mapping: Dict[str, str] = (
            get_nested_key(disease_yaml, ["disease", "rate_to_tag_mapping"], {})
        )
        self.symptom_tags: Dict[str, int] = {
            tag["name"]: tag["value"]
            for tag in get_nested_key(disease_yaml, ["disease", "symptom_tags"], [])
        }
        self.unrated_tags: List[str] = get_nested_key(disease_yaml, ["disease", "unrated_tags"], [])
        self.infection_outcome_rates: List[dict] = (
            get_nested_key(disease_yaml, ["disease", "infection_outcome_rates"], [])
        )

        self._rates_structure: Dict[str, Union[None, Dict[str, float]]] = None  # Initialize to None



    @property
    def rates_structure(self) -> Dict[str, Dict[str, Dict[str, Union[None, Dict[str, float]]]]]:
        """
        Retrieve or initialize the rates structure.

        The rates structure is a nested dictionary mapping rate parameters, population sectors,
        and genders to their precomputed values.

        Returns
        -------
        Dict[str, Dict[str, Dict[str, Union[None, Dict[str, float]]]]]
            A nested dictionary where keys are parameters, population sectors (e.g., 'gp', 'ch'),
            and genders ('male', 'female').
        """
        if self._rates_structure is None:
            self._rates_structure = {
                outcome["parameter"]: {
                    "gp": {"male": None, "female": None},
                    "ch": {"male": None, "female": None}
                }
                for outcome in self.infection_outcome_rates
            }
        return self._rates_structure

    def get_precomputed_rates(
        self, rates_df: pd.DataFrame, population: str, sex: str, parameter: str
    ) -> Dict[str, float]:
        """
        Retrieve or compute precomputed rates for a given parameter, population, and gender.

        Parameters
        ----------
        rates_df : pd.DataFrame
            A DataFrame containing rate values indexed by age bins.
        population : str
            The population type (e.g., 'ch', 'gp').
        sex : str
            The sex of the individual ('male' or 'female').
        parameter : str
            The rate parameter to retrieve or compute (e.g., 'hospital', 'ifr').

        Returns
        -------
        Dict[str, float]
            A dictionary mapping age bins to precomputed rate values.

        Raises
        ------
        ValueError
            If the specified column (constructed from population, parameter,
            and sex) is not found in the DataFrame.
        """
        # Check if rates are already computed for this parameter, population, and gender
        if self.rates_structure[parameter][population][sex] is not None:
            return self.rates_structure[parameter][population][sex]

        column_name = f"{population}_{parameter}_{sex}"

        if column_name not in rates_df.columns:
            raise ValueError(f"Column '{column_name}' not found in the DataFrame.")

        # Store the precomputed rates in the nested structure
        self.rates_structure[parameter][population][sex] = rates_df[column_name].to_dict()


        rate = {
            age_bin: float(value)
            for age_bin, value in self.rates_structure[parameter][population][sex].items()
        }
        return rate

    def map_rate_to_tag(self, rate_name: str) -> str:
        """
        Map a rate name to its corresponding symptom tag using the rate-to-tag mapping.

        Parameters
        ----------
        rate_name : str
            The name of the rate in the CSV or configuration.

        Returns
        -------
        str
            The corresponding symptom tag name.

        Raises
        ------
        KeyError
            If the rate name is not found in the mapping.
        """
        if rate_name not in self.rate_to_tag_mapping:
            raise KeyError(
                f"Rate '{rate_name}' is not mapped to a symptom tag."
            )
        return self.rate_to_tag_mapping[rate_name]

    def get_tag_for_rate(self, rate_name: str) -> int:
        """
        Get the tag value corresponding to a rate name using the mapping.

        Parameters
        ----------
        rate_name : str
            The name of the rate in the CSV or configuration.

        Returns
        -------
        int
            The tag value corresponding to the rate name.

        Raises
        ------
        KeyError
            If the rate name or tag is not found in the configuration.
        """
        tag_name = self.map_rate_to_tag(rate_name)
        return self.symptom_tags[tag_name]

    def get_rates_file(self) -> str:
        """
        Retrieve the path to the infection outcome rates file.

        Returns
        -------
        str
            Path to the rates file.
        """
        return self.rates_file

class InteractionManager:
    """
    Manages interaction-related configurations for a specific disease.

    This class loads interaction settings from a YAML file and initializes
    attributes related to disease susceptibility, interaction coefficients,
    contact matrices, and interactive groups.

    Attributes:
        susceptibilities (dict): Susceptibility values for different groups.
        alpha_physical (float or None): Physical interaction coefficient.
        betas (dict): Beta coefficients for interaction types.
        contact_matrices (dict): Contact matrices for population groups.
    """

    def __init__(self, disease_name: str):

        self.disease_name = disease_name.lower()
        interaction_path = (
            BASE_PATH /
            "configs/defaults/interaction" /
            f"interaction_{self.disease_name}.yaml"
        )
        # Load the interaction YAML file
        self._interaction_yaml = load_yaml(interaction_path)
        # Initialize private attributes
        self._susceptibilities = self._interaction_yaml.get("susceptibilities", {})
        self._alpha_physical = self._interaction_yaml.get("alpha_physical", None)
        self._betas = self._interaction_yaml.get("betas", {})
        self._contact_matrices = self._interaction_yaml.get("contact_matrices", {})

    @property
    def susceptibilities(self) -> dict:
        """Retrieve susceptibility values for different groups."""
        return self._susceptibilities

    @property
    def alpha_physical(self) -> Optional[float]:
        """Retrieve the physical interaction coefficient (alpha)."""
        return self._alpha_physical

    @property
    def betas(self) -> dict:
        """Retrieve beta coefficients for interaction types."""
        return self._betas

    @property
    def contact_matrices(self) -> dict:
        """Retrieve the contact matrices for population groups."""
        return self._contact_matrices

class SymptomManager:
    """
    Manages symptom-related configurations for a specific disease.

    This class initializes and processes symptom-related attributes for a disease
    based on its YAML configuration. It provides functionality to retrieve 
    symptom tag indices, categories, and default stages.

    Attributes:
        disease_yaml (dict): The YAML configuration of the disease.
        symptom_tags (dict): Mapping of symptom tag names to their values.
        default_lowest_stage (str): The default lowest stage of symptoms.
        default_lowest_stage_index (int): Index of the default lowest symptom stage.
        severe_symptom (list): List of tag values for severe symptoms.
        stay_at_home (list): List of tag values for stay-at-home symptoms.
        max_mild_symptom (str or None): Maximum mild symptom tag.
    """
    def __init__(self, disease_yaml: dict):
        # Initialize attributes from the disease YAML
        if "disease" not in disease_yaml:
            raise ValueError("The provided YAML does not contain a 'disease' key.")

        self.disease_yaml: dict = disease_yaml
        self.symptom_tags: Dict[str, int] = {
            tag["name"]: tag["value"]
            for tag in get_nested_key(disease_yaml, ["disease", "symptom_tags"], [])
        }
        settings = get_nested_key(disease_yaml, ["disease", "settings"], {})
        self.default_lowest_stage: str = settings.get("default_lowest_stage", "unknown")
        self._max_mild_symptom: Optional[str] = settings.get("max_mild_symptom_tag")
        self.severe_symptom = self._resolve_tags("severe_symptoms_stay_at_home_stage")
        self.stay_at_home = self._resolve_tags("stay_at_home_stage")


    @property
    def default_lowest_stage_index(self) -> int:
        """
        Retrieve the index of the default lowest stage.

        Returns
        -------
        int
            The index of the default lowest stage.

        Raises
        ------
        ValueError
            If the default lowest stage is not found in the symptom tags.
        """
        if self.default_lowest_stage not in self.symptom_tags:
            raise ValueError(
                f"Default stage '{self.default_lowest_stage}' not in symptom tags."
            )
        return self.symptom_tags[self.default_lowest_stage]

    @property
    def max_mild_symptom_tag(self) -> Optional[int]:
        """
        Retrieve the index of the maximum mild symptom tag.

        Returns
        -------
        Optional[int]
            The value corresponding to `max_mild_symptom_tag`.

        Raises
        ------
        ValueError
            If `max_mild_symptom_tag` is not defined or is not valid.
        """
        if self._max_mild_symptom is None:
            raise ValueError("'max_mild_symptom_tag' is not defined in the configuration.")
        if self._max_mild_symptom not in self.symptom_tags:
            raise ValueError(
                f"'max_mild_symptom_tag' ({self._max_mild_symptom}) is not a valid symptom tag."
            )
        return self.symptom_tags[self._max_mild_symptom]

    def _resolve_tags(self, category: str) -> List[int]:
        """
        Resolve tags dynamically for a given category from the configuration.

        Parameters
        ----------
        category : str
            The category in the YAML file to retrieve the symptom tags for.

        Returns
        -------
        List[int]
            A list of tag values corresponding to the given category.
        """
        stage_definitions = get_nested_key(self.disease_yaml, ["disease", "settings", category], [])
        return [
            self.symptom_tags.get(stage.get("name"), -1)
            for stage in stage_definitions
            if "name" in stage and stage["name"] in self.symptom_tags
        ]

    def get_tag_value(self, tag_name: str) -> int:
        """
        Get the value of a symptom tag by its name.

        Parameters
        ----------
        tag_name : str
            The name of the symptom tag.

        Returns
        -------
        int
            The value of the symptom tag.

        Raises
        ------
        KeyError
            If the tag name is not found in the configuration.
        """
        if tag_name not in self.symptom_tags:
            raise KeyError(f"Symptom tag '{tag_name}' not found.")
        return self.symptom_tags[tag_name]


class VaccinationManager:
    """
    Manages vaccination-related configurations for a specific disease.

    This class loads and processes vaccination-related settings from a YAML file. 
    It initializes attributes for available vaccines and vaccination campaigns.

    Attributes:
        vaccination_yaml (dict): The YAML configuration for vaccinations.
        vaccines (dict): Dictionary of vaccines and their configurations.
        vaccination_campaigns (dict): Dictionary of vaccination campaigns.
    """
    def __init__(self, disease_name: str):

        vaccination_path = (
            paths.configs_path /
            f"defaults/epidemiology/vaccines/vaccines_{disease_name}.yaml"
        )

        # Load the vaccination YAML
        with open(vaccination_path, "r", encoding="utf-8") as f:
            self.vaccination_yaml = yaml.safe_load(f)

        # Initialize attributes
        self.vaccines = self.vaccination_yaml.get("vaccines", {}) or {}
        self.vaccination_campaigns = self.vaccination_yaml.get("vaccination_campaigns", {}) or {}

    def get_vaccines(self) -> dict:
        """
        Retrieve all vaccines.

        Returns
        -------
        dict
            A dictionary of vaccines.
        """
        return self.vaccines

    def get_vaccination_campaigns(self) -> dict:
        """
        Retrieve all vaccination campaigns.

        Returns
        -------
        dict
            A dictionary of vaccination campaigns.
        """
        return self.vaccination_campaigns

class PolicyManager:
    """
    Manages policy configurations for a specific disease.
    """

    def __init__(self, disease_name: str):
        policy_path = paths.configs_path / f"defaults/policy/policy_{disease_name}.yaml"
        with open(policy_path, "r", encoding="utf-8") as f:
            self.policy_yaml = yaml.safe_load(f) or {}

    def get_policy_data(self, policy_name: str) -> dict:
        """
        Retrieve the configuration for a specific policy.

        Parameters
        ----------
        policy_name : str
            Name of the policy.

        Returns
        -------
        dict
            Configuration dictionary for the policy.
        """
        return self.policy_yaml.get(policy_name, {})

    def get_all_policies(self) -> dict:
        """
        Retrieve all categorized policies.

        Returns
        -------
        dict
            A dictionary of all policies organized by categories.
        """
        return self.policy_yaml
    