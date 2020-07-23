import copy
import datetime
import re
import sys
import numpy as np
from abc import ABC, abstractmethod
from typing import Union, Optional, List, Dict

import yaml

from june import paths
from june.demography.person import Person
from june.groups.leisure import Leisure
from june.infection.symptom_tag import SymptomTag
from june.interaction import Interaction

default_config_filename = paths.configs_path / "defaults/policy/policy.yaml"


def str_to_class(classname):
    return getattr(sys.modules["june.policy"], classname)


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
        self.start_time = self.read_date(start_time)
        self.end_time = self.read_date(end_time)

    @staticmethod
    def read_date(date: Union[str, datetime.datetime]) -> datetime.datetime:
        """
        Read date in two possible formats, either string or datetime.date, both
        are translated into datetime.datetime to be used by the simulator

        Parameters
        ----------
        date:
            date to translate into datetime.datetime

        Returns
        -------
            date in datetime format
        """
        if type(date) is str:
            return datetime.datetime.strptime(date, "%Y-%m-%d")
        elif isinstance(date, datetime.date):
            return datetime.datetime.combine(date, datetime.datetime.min.time())
        else:
            raise TypeError("date must be a string or a datetime.date object")

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




class Policies:
    def __init__(self, policies=None):
        self.policies = policies

    @classmethod
    def from_file(
        cls, config_file=default_config_filename,
    ):
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        policies = []
        for policy, policy_data in config.items():
            camel_case_key = "".join(x.capitalize() or "_" for x in policy.split("_"))
            if "start_time" not in policy_data:
                for policy_i, policy_data_i in policy_data.items():
                    if (
                        "start_time" not in policy_data_i.keys()
                        or "end_time" not in policy_data_i.keys()
                    ):
                        raise ValueError("policy config file not valid.")
                    policies.append(str_to_class(camel_case_key)(**policy_data_i))
            else:
                policies.append(str_to_class(camel_case_key)(**policy_data))
        return Policies(policies=policies)

    def get_active_policies_for_type(self, policy_type, date):
        return [
            policy
            for policy in self.policies
            if policy.policy_type == policy_type and policy.is_active(date)
        ]

    def __iter__(self):
        return iter(self.policies)

class PolicyCollection(ABC):
    def __init__(self, policies: List[Policy]):
        """
        A collection of like policies active on the same date
        """
        self.policies = policies

    @classmethod
    def get_active_policies(cls, policies: Policies, date: datetime):
        policies = policies.get_active_policies_for_type(
            policy_type=cls.policy_type, date=date
        )
        return cls(policies)

    def apply(self):
        raise NotImplementedError()
