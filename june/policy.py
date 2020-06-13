from june import paths
import re
from datetime import datetime
import yaml
from abc import ABC, abstractmethod

default_config_filename = paths.configs_path / "defaults/policy.yaml"


class Policy(ABC):
    def __init__(self, start_time=None, end_time=None):
        self.spec = self.get_spec()
        if start_time is None and end_time is None:
            self.always_active = True
        else:
            self.always_active = False
            self.start_time = start_time
            self.end_time = end_time

    def get_spec(self) -> str:
        """
        Returns the speciailization of the group.
        """
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()

    def is_active(self, date):
        if self.always_active:
            return True
        elif date >= self.start_time and date <= self.end_time:
            return True
        return False


class PermanentPolicy(Policy):
    def must_stay_at_home(self, person: "Person", time, activities):
        return (
            person.health_information is not None
            and person.health_information.must_stay_at_home
        )


# TODO: not working yet, need to keep track of symptom_onset even for recovered/dead people
class Quarantine(Policy):
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

    def must_stay_at_home(self, person: "Person", days: float):
        return person.symptom_onset is not None and (
            days < person.symptoms_onset + self.n_days
        )

    def must_stay_at_home_because_of_housemates(self, person: "Person", days: float):
        pass


class Shielding(Policy):
    def __init__(
        self, start_time: "datetime", end_time: "datetime", min_age: int,
    ):
        super().__init__(start_time, end_time)
        self.min_age = min_age

    def must_stay_at_home(self, person: "Person", days, activities):
        return person.age >= self.min_age


class CloseSchools(Policy):
    def __init__(
        self, start_time: "datetime", end_time: "datetime", years_to_close="all"
    ):
        super().__init__(start_time, end_time)
        self.years_to_close = years_to_close

    def must_stay_at_home(self, person: "Person", days: float, activities):
        if person.primary_activity is not None:
            if self.years_to_close == "all":
                return (
                    "primary_activity" in activities
                    and person.primary_activity.group.spec == "school"
                )
            else:
                return (
                    "primary_activity" in activities
                    and person.primary_activity.group.spec == "school"
                    and person.age in self.years_to_close
                )
        return


class CloseCompanies(Policy):
    def __init__(
        self, start_time: "datetime", end_time: "datetime", sectors_to_close="all"
    ):
        super().__init__(start_time, end_time)
        self.sectors_to_close = sectors_to_close

    def must_stay_at_home(self, person: "Person", days: float, activities):
        if person.primary_activity is not None:
            if self.sectors_to_close == "all":
                return (
                    # TODO: potentially could add commute here
                    "primary_activity" in activities
                    and person.primary_activity.group.spec == "company"
                )
            else:
                return (
                    "primary_activity" in activities
                    and person.primary_activity.group.spec == "company"
                    and person.sector in self.sectors_to_close
                )
        return


# TODO: we should unify this policy, the action of the class should be here, also its parameters (like beta factors ...)
class SocialDistancing(Policy):
    def __init__(self, name, start_time: "datetime", end_time: "datetime"):
        super().__init__(start_time, end_time)
        self.name = name


class Policies:
    def __init__(self, policies=[], config=None):
        self.config = config
        self.policies = policies
        self.social_distancing = False
        self.social_distancing_start = 0
        self.social_distancing_end = 0

        for policy in self.policies:
            if hasattr(policy, "name") and policy.name == "social_distance":
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

    def must_stay_at_home(self, person, date, activities):
        if person.hospital is None:
            for policy in self.policies:
                if policy.is_active(date) and hasattr(policy, "must_stay_at_home"):
                    if policy.must_stay_at_home(person, date, activities):
                        return True
        return False

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
