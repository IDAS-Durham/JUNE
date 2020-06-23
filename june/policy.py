import copy
import datetime
import re
import sys
from abc import ABC, abstractmethod
from typing import Union, Optional, List

import yaml

from june import paths
from june.demography.person import Person

# TODO: reduce leisure attendance

default_config_filename = paths.configs_path / "defaults/policy.yaml"


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
        return self.start_time <= date <= self.end_time


class SocialDistancing(Policy):
    def __init__(
            self,
            start_time: Union[str, datetime.datetime] = "1900-01-01",
            end_time: Union[str, datetime.datetime] = "2100-01-01",
            beta_factor: Optional[dict] = None,
    ):
        super().__init__(start_time, end_time)
        if beta_factor is None:
            self.beta_factor = {}
        else:
            self.beta_factor = beta_factor


class SkipActivity(Policy):
    """
    Template for policies that will ban an activity for a person
    """
    @abstractmethod
    def skip_activity(self, person: "Person", activities: List[str]) -> bool:
        """
        Returns True if the activity is to be skipped, otherwise False
        """
        pass

    def remove_activity(
            self, activities: List[str], activity_to_remove: str
    ) -> List[str]:
        """
        Remove an activity from a list of activities

        Parameters
        ----------
        activities:
            list of activities
        activity_to_remove:
            activity that will be removed from the list
        """
        return [activity for activity in activities if activity != activity_to_remove]


class StayHome(Policy):
    """
    Template for policies that will force someone to stay at home
    """

    @abstractmethod
    def must_stay_at_home(self, person: "Person", days_from_start: float):
        """
        Returns True if Person must stay at home, otherwise False

        Parameters
        ----------
        person: 
            person to whom the policy is being applied

        days_from_start:
            time past from beginning of simulation, in units of days
        """
        pass


class CloseLeisureVenue(Policy):
    def __init__(
            self,
            start_time: Union[str, datetime.datetime] = "1900-01-01",
            end_time: Union[str, datetime.datetime] = "2100-01-01",
            venues_to_close=("cinemas", "groceries"),
    ):
        """
        Template for policies that will close types of leisure venues

        Parameters
        ----------
        start_time:
            date at which to start applying the policy
        end_time:
            date from which the policy won't apply
        venues_to_close:
            list of leisure venues that will close
        """

        super().__init__(start_time, end_time)
        self.venues_to_close = venues_to_close


class PermanentPolicy(StayHome):
    def must_stay_at_home(self, person: "Person", days_from_start: float) -> bool:
        """
        Returns True if person has symptoms, otherwise False

        Parameters
        ----------
        person: 
            person to whom the policy is being applied

        days_from_start:
            time past from beginning of simulation, in units of days
        """
        return (
                person.health_information is not None
                and person.health_information.must_stay_at_home
        )


class Quarantine(StayHome):
    def __init__(
            self,
            start_time: Union[str, datetime.datetime] = "1900-01-01",
            end_time: Union[str, datetime.datetime] = "2100-01-01",
            n_days: int = 7,
            n_days_household: int = 14,
    ):
        """
        This policy forces people to stay at home for ```n_days``` days after they show symtpoms, and for ```n_days_household``` if someone else in their household shows symptoms

        Parameters
        ----------
        start_time:
            date at which to start applying the policy
        end_time:
            date from which the policy won't apply
        n_days:
            days for which the person has to stay at home if they show symtpoms
        n_days_household:
            days for which the person has to stay at home if someone in their household shows symptoms
        """
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.n_days_household = n_days_household

    # TODO: if someone recovers or dies it will stop checking !
    def must_stay_at_home(self, person: "Person", days_from_start: float):
        return self.must_stay_at_home_housemates(
            person, days_from_start, self.n_days_household
        ) or self.must_stay_at_home_symptoms(person, days_from_start, self.n_days)

    @staticmethod
    def must_stay_at_home_symptoms(
            person: "Person", days_from_start: float, n_days_at_home
    ):
        try:
            release_day = person.health_information.time_of_symptoms_onset + n_days_at_home
            return release_day > days_from_start > person.health_information.time_of_symptoms_onset
        except (TypeError, AttributeError) as error:
            return False

    def must_stay_at_home_housemates(
            self, person: "Person", days_from_start: float, n_days_at_home
    ):
        for housemate in person.housemates:
            if self.must_stay_at_home_symptoms(
                    housemate, days_from_start, n_days_at_home
            ):
                return True
        return False


class Shielding(StayHome):
    def __init__(
            self, start_time: str, end_time: str, min_age: int,
    ):
        super().__init__(start_time, end_time)
        self.min_age = min_age

    def must_stay_at_home(self, person: "Person", days_from_start: float):
        return person.age >= self.min_age


# TODO: should we automatically have parents staying with children left alone?
class CloseSchools(SkipActivity):
    def __init__(
            self, start_time: str, end_time: str, years_to_close=None, full_closure=None,
    ):
        super().__init__(start_time, end_time)
        self.full_closure = full_closure
        self.years_to_close = years_to_close

    def skip_activity(self, person: "Person", activities):
        if (
                person.primary_activity is not None
                and person.primary_activity.group.spec == "school"
        ):
            if self.full_closure or person.age in self.years_to_close:
                return self.remove_activity(activities, "primary_activity")
        return activities


class CloseUniversities(SkipActivity):
    def __init__(
            self, start_time: str, end_time: str,
    ):
        super().__init__(start_time, end_time)

    def skip_activity(self, person: "Person", activities):
        if (
                person.primary_activity is not None
                and person.primary_activity.group.spec == "university"
        ):
            return self.remove_activity(activities, "primary_activity")
        return activities


class CloseCompanies(SkipActivity):
    def __init__(
            self, start_time: str, end_time: str, sectors_to_close=None, full_closure=None,
    ):
        super().__init__(start_time, end_time)
        self.full_closure = full_closure
        self.sectors_to_close = sectors_to_close

    def skip_activity(self, person: "Person", activities):
        if (
                person.primary_activity is not None
                and person.primary_activity.group.spec == "company"
        ):
            if self.full_closure or person.sector in self.sectors_to_close:
                return self.remove_activity(activities, "primary_activity")
        return activities


class Policies:
    def __init__(self, policies=None):
        self.policies = [PermanentPolicy()] + (policies or list())
        self.social_distancing = False
        self.social_distancing_start = 0
        self.social_distancing_end = 0

        for policy in self.policies:
            if isinstance(policy, SocialDistancing):
                self.social_distancing_policy = policy
                self.social_distancing = True
                self.social_distancing_start = policy.start_time
                self.social_distancing_end = policy.end_time

    @classmethod
    def from_file(
            cls, config_file=default_config_filename,
    ):
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        policies = []
        for key, value in config.items():
            camel_case_key = "".join(x.capitalize() or "_" for x in key.split("_"))
            policies.append(str_to_class(camel_case_key)(**value))
        return Policies(policies=policies)

    def get_active_policies_for_type(self, policy_type, date):
        return [
            policy
            for policy in self.policies
            if isinstance(policy, policy_type) and policy.is_active(date)
        ]

    def stay_home_policies(self, date):
        return self.get_active_policies_for_type(policy_type=StayHome, date=date)

    def skip_activity_policies(self, date):
        return self.get_active_policies_for_type(policy_type=SkipActivity, date=date)

    def social_distancing_policies(self, date):
        return self.get_active_policies_for_type(
            policy_type=SocialDistancing, date=date
        )

    def close_venues_policies(self, date):
        return self.get_active_policies_for_type(
            policy_type=CloseLeisureVenue, date=date
        )

    def must_stay_at_home(self, person, date, days_from_start):
        if person.hospital is None:
            for policy in self.stay_home_policies(date):
                if policy.must_stay_at_home(person, days_from_start):
                    return True
        return False

    def apply_social_distancing_policy(self, betas, time):
        '''
        Implement social distancing policy
        
        -----------
        Parameters:
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta

        Assumptions:
        - Currently we assume that social distancing is implemented first and this affects all
          interactions and intensities globally
        - Currently we assume that the changes are not group dependent


        TODO:
        - Implement structure for people to adhere to social distancing with a certain compliance
        - Check per group in config file
        '''
        betas_new = copy.deepcopy(betas)
        for group in betas:
            betas_new[group] = self.social_distancing_policy.beta_factor[group] * betas_new[group]
        return betas_new

    def get_beta_factors(self, group):
        pass

    def apply_activity_ban(self, person, date, activities):
        for policy in self.skip_activity_policies(date):
            activities = policy.skip_activity(person, activities)
        return activities

    def find_closed_venues(self, date):
        closed_venues = set()
        for policy in self.close_venues_policies(date):
            closed_venues.update(policy.venues_to_close)
        return closed_venues


def str_to_class(classname):
    return getattr(sys.modules["june.policy"], classname)
