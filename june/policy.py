from june import paths
import re
from datetime import datetime
import yaml
from abc import ABC, abstractmethod

default_config_filename = paths.configs_path / "defaults/policy.yaml"

# TODO: finish closure of leisure buildings + reduce leisure attendance
class Policy(ABC):
    def __init__(self, start_time=datetime(1900, 1, 1), end_time=datetime(2100, 1, 1)):
        self.spec = self.get_spec()
        self.start_time = start_time
        self.end_time = end_time

    def get_spec(self) -> str:
        """
        Returns the speciailization of the group.
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()

    def is_active(self, date):
        if date >= self.start_time and date <= self.end_time:
            return True
        return False


# TODO: we should unify this policy, the action of the class should be here, also its parameters (like beta factors ...)
class SocialDistancing(Policy):
    def __init__(self, start_time=datetime(1900, 1, 1), end_time=datetime(2100, 1, 1)):
        super().__init__(start_time, end_time)
        self.policy_type = "social_distancing"


class SkipActivity(Policy):
    def __init__(self, start_time=datetime(1900, 1, 1), end_time=datetime(2100, 1, 1)):
        super().__init__(start_time, end_time)
        self.policy_type = "skip_activity"

    @abstractmethod
    def skip_activity(self, person, activities):
        pass

    def remove_activity(self, activities, activity_to_remove):
        return [activity for activity in activities if activity != activity_to_remove]


class StayHome(Policy):
    def __init__(self, start_time=datetime(1900, 1, 1), end_time=datetime(2100, 1, 1)):
        super().__init__(start_time, end_time)
        self.policy_type = "stay_home"

    @abstractmethod
    def must_stay_at_home(self, person, days_from_start):
        pass

class CloseLeisureVenue(Policy):
    def __init__(
        self,
        start_time=datetime(1900, 1, 1),
        end_time=datetime(2100, 1, 1),
        venues_to_close=["cinemas", "groceries"],
    ):
        super().__init__(start_time, end_time)
        self.policy_type = "close_leisure_venue"
        self.venues_to_close = venues_to_close

class PermanentPolicy(StayHome):
    def must_stay_at_home(self, person: "Person", days_from_start):
        return (
            person.health_information is not None
            and person.health_information.must_stay_at_home
        )


class Quarantine(StayHome):
    def __init__(
        self,
        start_time: "datetime",
        end_time: "datetime",
        n_days: int = 7,
        n_days_household: int = 14,
    ):
        super().__init__(start_time, end_time)
        self.n_days = n_days
        self.n_days_household = n_days_household

    # TODO: if someone recovers or dies it will stop checking !
    def must_stay_at_home(self, person: "Person", days_from_start: float):
        return self.must_stay_at_home_housemates(
            person, days_from_start, self.n_days_household
        ) or self.must_stay_at_home_symptoms(person, days_from_start, self.n_days)

    def must_stay_at_home_symptoms(
        self, person: "Person", days_from_start: float, n_days_at_home
    ):
        return (
            person.health_information is not None
            and person.health_information.time_of_symptoms_onset is not None
            and days_from_start
            < person.health_information.time_of_symptoms_onset + n_days_at_home
            and days_from_start > person.health_information.time_of_symptoms_onset
        )

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
        self, start_time: "datetime", end_time: "datetime", min_age: int,
    ):
        super().__init__(start_time, end_time)
        self.min_age = min_age

    def must_stay_at_home(self, person: "Person", days_from_start: float):
        return person.age >= self.min_age


# TODO: should we automatically have parents staying with children left alone?
class CloseSchools(SkipActivity):
    def __init__(
        self,
        start_time: "datetime",
        end_time: "datetime",
        years_to_close=None,
        full_closure=None,
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


class CloseCompanies(SkipActivity):
    def __init__(
        self,
        start_time: "datetime",
        end_time: "datetime",
        sectors_to_close=None,
        full_closure=None,
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
    def __init__(self, policies=[], config=None):
        self.config = config
        self.policies = policies
        self.social_distancing = False
        self.social_distancing_start = 0
        self.social_distancing_end = 0

        for policy in self.policies:
            if policy.policy_type == "social_distancing":
                self.social_distancing = True
                self.social_distancing_start = policy.start_time
                self.social_distancing_end = policy.end_time

    @classmethod
    def from_file(
        cls, policies: list = [], config_file=default_config_filename,
    ):

        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        return Policies(policies, config)

    def get_active_policies_for_type(self, policy_type, date):
        return [
            policy
            for policy in self.policies
            if policy.policy_type == policy_type and policy.is_active(date)
        ]

    def stay_home_policies(self, date):
        return self.get_active_policies_for_type(policy_type="stay_home", date=date)

    def skip_activity_policies(self, date):
        return self.get_active_policies_for_type(policy_type="skip_activity", date=date)

    def social_distancing_policies(self, date):
        return self.get_active_policies_for_type(
            policy_type="social_distancing", date=date
        )

    def close_venues_policies(self, date):
        return self.get_active_policies_for_type(
            policy_type="close_leisure_venue", date=date
        )

    def must_stay_at_home(self, person, date, days_from_start):
        if person.hospital is None:
            for policy in self.stay_home_policies(date):
                if policy.must_stay_at_home(person, days_from_start):
                    return True
        return False

    def apply_activity_ban(self, person, date, activities):
        for policy in self.skip_activity_policies(date):
            activities = policy.skip_activity(person, activities)
        return activities

    def find_closed_venues(self, date):
        closed_venues = set()
        for policy in self.close_venues_policies(date):
            closed_venues.update(policy.venues_to_close)
        return closed_venues

    def social_distancing_policy(self, alpha, betas, time):
        """
        Implement social distancing policy
        
        -----------
        Parameters:
        alphas: e.g. (float) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).alpha
        betas: e.g. (dict) from DefaultInteraction, e.g. DefaultInteraction.from_file(selector=selector).beta

        Assumptions:
        - Currently we assume that social distancing is implemented first and this affects all
          interactions and intensities globally
        - Currently we assume that the changes are not group dependent


        TODO:
        - Implement structure for people to adhere to social distancing with a certain compliance
        - Check per group in config file
        """
        # TODO: should probably leave alpha value for households untouched!

        betas_new = betas.copy()

        if self.config is None:
            alpha_new = alpha * 1.0
        else:
            alpha_new = alpha * self.config["social distancing"]["alpha factor"]

        for group in betas:
            if self.config is None:
                if group != "household":
                    betas_new[group] = betas_new[group] * 0.5
            else:
                betas_new[group] = (
                    betas_new[group]
                    * self.config["social distancing"]["beta factor"][group]
                )

        return alpha_new, betas_new
