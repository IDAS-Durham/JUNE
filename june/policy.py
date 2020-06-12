from june import paths
from datetime import datetime
import yaml

default_config_filename = paths.configs_path / "defaults/policy.yaml"


class Policy:
    def __init__(self, policy="default", start_time=None, end_time=None):
        self.name = policy
        if start_time is None and end_time is None:
            self.always_active = True
        else:
            self.start_time = start_time
            self.end_time = end_time

    @property
    def is_active(self, date):
        if self.always_active:
            return True
        elif date > self.start_time and date < self.end_time:
            return True
        return False

    def must_stay_at_home(self, person: "Person", timer, activities):
        return (
            person.health_information is not None
            and person.health_information.must_stay_at_home
        )


class Quarentine(Policy):
    def __init__(
        self,
        start_time: "datetime",
        end_time: "datetime",
        n_days: int,
        n_days_household: int,
    ):
        super().__init__("quarantine", start_time, end_time)
        self.n_days = n_days
        self.n_days_household = n_days_household

    def must_stay_at_home(self, person: "Person", days: float):
        return person.symptom_onset is not None and (
            days < person.symptoms_onset + self.n_days
        ) and person.hospital is None


class CloseSchools(Policy):
    def __init__(
        self,
        start_time: "datetime",
        end_time: "datetime",
        years_to_close=[5, 6, 7, 8, 9, 10, 11, 12],
    ):
        super().__init__("quarantine", start_time, end_time)
        self.years_to_close = years_to_close

    def must_stay_at_home(self, person: "Person", days: float, activities):
        return (
            person.hospital is None and 
            "primary_activity" in activities
            and person.primary_activity.group.spec == "school"
            and person.age in self.years_to_close
        )


class CloseCompanies(Policy):
    def __init__(
        self, start_time: "datetime", end_time: "datetime", sectors=["P", "Q"]
    ):
        super().__init__("quarantine", start_time, end_time)
        self.sectors = sectors

    def must_stay_at_home(self, person: "Person", days: float, activities):
        return (
            person.hospital is None and 
            "primary_activity" in activities
            and person.primary_activity.group.spec == "company"
            and person.sector in self.sectors
        )


class Policies:
    def __init__(self, policies=[], config=None):
        self.config = config
        self.policies = policies
        self.social_distancing = False
        self.social_distancing_start = 0
        self.social_distancing_end = 0

        for policy in self.policies:
            if policy.name == "social_distance":
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

    def must_stay_at_home(self, person, timer, activities):
        for policy in self.policies:
            if hasattr(policy, "must_stay_at_home") and policy.active(timer.date):
                if policy.must_stay_at_home(person, timer.now, activities):
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
