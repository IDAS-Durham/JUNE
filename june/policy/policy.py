import datetime
from inspect import signature
import re
from abc import ABC
from typing import List, Union

import yaml

from june import paths
from june.epidemiology.infection.disease_config import DiseaseConfig
from june.utils import read_date, str_to_class

default_config_filename = paths.configs_path / "defaults/policy/policy.yaml"


class Policy(ABC):
    def __init__(
        self,
        start_time: Union[str, datetime.datetime] = "1900-01-01",
        end_time: Union[str, datetime.datetime] = "2100-01-01",
    ):
        """
        Template for a general policy.

        Parameters
        ----------
        start_time:
            date at which to start applying the policy
        end_time:
            date from which the policy won't apply
        """
        self.spec = self.get_spec()
        self.start_time = read_date(start_time)
        self.end_time = read_date(end_time)

    def get_spec(self) -> str:
        """
        Returns the speciailization of the policy.
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()

    def is_active(self, date: datetime.datetime) -> bool:
        """
        Returns true if the policy is active, false otherwise

        Parameters
        ----------
        date:
            date to check
        """

        return self.start_time <= date < self.end_time

    def initialize(self, world, date, record=None):
        pass


class Policies:
    def __init__(self, policies=None):
        """
        Initialize Policies and its categorized policy types.

        Parameters
        ----------
        policies : list, optional
            A list of initialized policy objects.
        """
        self.policies = policies or []

        # Initialize policy-specific categories
        self.individual_policies = None
        self.interaction_policies = None
        self.medical_care_policies = None
        self.leisure_policies = None
        self.regional_compliance = None
        self.tiered_lockdown = None

        # Initialize policy categories lazily
        self._initialize_policy_categories()

    def _initialize_policy_categories(self):
        """
        Initialize specific policy categories using the from_policies method.
        """
        from june.policy import (
            IndividualPolicies,
            InteractionPolicies,
            MedicalCarePolicies,
            LeisurePolicies,
            RegionalCompliances,
            TieredLockdowns,
        )

        self.individual_policies = IndividualPolicies.from_policies(self)
        self.interaction_policies = InteractionPolicies.from_policies(self)
        self.medical_care_policies = MedicalCarePolicies.from_policies(self)
        self.leisure_policies = LeisurePolicies.from_policies(self)
        self.regional_compliance = RegionalCompliances.from_policies(self)
        self.tiered_lockdown = TieredLockdowns.from_policies(self)

    @classmethod
    def from_file(
        cls, disease_config: DiseaseConfig, base_policy_modules=("june.policy",)
    ):
        """
        Load policies from the configuration file.

        Parameters
        ----------
        disease_config : DiseaseConfig
            The disease configuration object.
        base_policy_modules : tuple
            The base modules to search for policy classes.

        Returns
        -------
        Policies
            The loaded Policies object.
        """
        # Access the policy data via PolicyManager
        policy_manager = disease_config.policy_manager
        policy_data = policy_manager.get_all_policies()
        policies = []

        try:
            for policy_name, config in policy_data.items():
                cls._process_policy(policies, policy_name, config, base_policy_modules, disease_config)
            
        except Exception as e:
            import traceback
            print(f"Error loading policies: {e}")
            print(traceback.format_exc())

        # Return the Policies object with the loaded policies
        return cls(policies=policies)

    @staticmethod
    def _process_policy(policies, policy_name, config, base_policy_modules, disease_config):
        """
        Process a single policy or policy group.

        Parameters
        ----------
        policies : list
            List to append policies to.
        policy_name : str
            Name of the policy.
        config : dict
            Configuration for the policy.
        base_policy_modules : tuple
            Modules to search for policy classes.
        disease_config : DiseaseConfig
            The disease configuration object.
        """
        # Skip empty configurations
        if not config:
            print(f"Skipping empty policy section: {policy_name}")
            return

        # Dynamically resolve the class
        camel_case_key = "".join(x.capitalize() for x in policy_name.split("_"))
        try:
            # Try to find policy class in any of the modules
            policy_class = None
            for module_name in base_policy_modules:
                try:
                    # Try to import the module
                    module = __import__(module_name, fromlist=[camel_case_key])
                    # Try to get the class
                    if hasattr(module, camel_case_key):
                        policy_class = getattr(module, camel_case_key)
                        break
                except ImportError:
                    print(f"  Module {module_name} not found, skipping...")
                    continue
            
            # If no class was found, raise error
            if policy_class is None:
                raise ValueError(f"Could not find class {camel_case_key} in any of the modules {base_policy_modules}")
            
            
            # Prepare to inspect the constructor
            init_signature = signature(policy_class.__init__)
            init_params = init_signature.parameters

            # Handle grouped policies
            if isinstance(config, dict) and "start_time" not in config:
                for sub_name, sub_config in config.items():
                    if isinstance(sub_config, dict):
                        filtered_data = Policies._filter_params(sub_config, init_params, disease_config)                    
                        policies.append(policy_class(**filtered_data))
            else:
                # Handle single policies
                filtered_data = Policies._filter_params(config, init_params, disease_config)
                policies.append(policy_class(**filtered_data))
        except Exception as e:
            print(f"Error processing policy {policy_name}: {e}")

    @staticmethod
    def _filter_params(config, init_params, disease_config):
        """
        Filter configuration parameters based on the policy class constructor.

        Parameters
        ----------
        config : dict
            Raw configuration.
        init_params : inspect.Parameters
            Constructor parameters of the policy class.
        disease_config : DiseaseConfig
            Disease configuration object for contextual arguments.

        Returns
        -------
        dict
            Filtered configuration suitable for the constructor.
        """
        # Check for parameters in config that aren't in init_params
        extra_params = [key for key in config.keys() if key not in init_params]
        if extra_params:
            print(f"WARNING: These parameters in YAML are not in constructor: {extra_params}")

        filtered_data = {key: value for key, value in config.items() if key in init_params}

        # Inject disease_config if required
        if "disease_config" in init_params:
            filtered_data["disease_config"] = disease_config

        return filtered_data
    
    def get_policies_for_type(self, policy_type: str):
        """
        Retrieve all policies of a specific type.

        Parameters
        ----------
        policy_type : str
            The type of policy to retrieve.

        Returns
        -------
        list
            A list of policies matching the specified type.
        """
        return [policy for policy in self.policies if getattr(policy, "policy_type", None) == policy_type]
    
    def __iter__(self):
        if self.policies is None:
            return iter([])
        return iter(self.policies)

    def init_policies(self, world, date, record=None):
        """
        This function is meant to be used for those policies that need world information to initialise,
        like policies depending on workers' behaviours during lockdown.
        """
        for policy in self:
            policy.initialize(world=world, date=date, record=record)


class PolicyCollection:
    def __init__(self, policies: List[Policy]):
        """
        A collection of like policies active on the same date
        """
        self.policies = policies
        self.policies_by_name = {
            self._get_policy_name(policy): policy for policy in policies
        }

    def _get_policy_name(self, policy):
        return re.sub(r"(?<!^)(?=[A-Z])", "_", policy.__class__.__name__).lower()

    @classmethod
    def from_policies(cls, policies: Policies):
        return cls(policies.get_policies_for_type(policy_type=cls.policy_type))

    def get_active(self, date: datetime):
        return [policy for policy in self.policies if policy.is_active(date)]

    def apply(self, active_policies):
        raise NotImplementedError()

    def __iter__(self):
        return iter(self.policies)

    def __getitem__(self, index):
        return self.policies[index]

    def get_from_name(self, name):
        return self.policies_by_name[name]

    def __contains__(self, policy_name):
        return policy_name in self.policies_by_name
