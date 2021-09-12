import operator
from random import random
import numpy as np
import datetime
from typing import List
from june.demography.person import Person
from .policy import Policy, PolicyCollection, Policies, read_date
from june import paths


class VaccinePlan:
    __slots__ = (
        "first_dose_date",
        "second_dose_date",
        "first_dose_effective_days",
        "second_dose_effective_days",
        "first_dose_sterilisation_efficacy",
        "second_dose_sterilisation_efficacy",
        "original_susceptibility",
        "first_dose_symptomatic_efficacy",
        "second_dose_symptomatic_efficacy",
        "original_effective_multiplier",
        "infection_ids",
    )

    def __init__(
        self,
        first_dose_date,
        second_dose_date,
        first_dose_effective_days,
        second_dose_effective_days,
        first_dose_sterilisation_efficacy,
        second_dose_sterilisation_efficacy,
        original_susceptibility,
        first_dose_symptomatic_efficacy,
        second_dose_symptomatic_efficacy,
        original_effective_multiplier,
    ):
        self.first_dose_date = first_dose_date
        self.first_dose_effective_days = first_dose_effective_days
        self.first_dose_sterilisation_efficacy = first_dose_sterilisation_efficacy
        self.first_dose_symptomatic_efficacy = first_dose_symptomatic_efficacy
        self.second_dose_date = second_dose_date
        self.second_dose_effective_days = second_dose_effective_days
        self.second_dose_sterilisation_efficacy = second_dose_sterilisation_efficacy
        self.second_dose_symptomatic_efficacy = second_dose_symptomatic_efficacy
        self.original_susceptibility = original_susceptibility
        self.original_effective_multiplier = original_effective_multiplier
        self.infection_ids = list(self.first_dose_sterilisation_efficacy.keys())

    @property
    def first_dose_effective_date(self):
        return self.first_dose_date + datetime.timedelta(
            days=self.first_dose_effective_days
        )

    @property
    def second_dose_effective_date(self):
        return self.second_dose_date + datetime.timedelta(
            days=self.second_dose_effective_days
        )

    def is_finished(self, date):
        if self.second_dose_date is None and date > self.first_dose_effective_date:
            return True
        elif (
            self.second_dose_date is not None and date > self.second_dose_effective_date
        ):
            return True
        return False

    def straight_line(self, n_days, p0, p1):
        m = (p1[1] - p0[1]) / (p1[0] - p0[0])
        c = p1[1] - (m * p1[0])
        return m * n_days + c

    def update_original_value(
        self, date, first_dose_efficacy, second_dose_efficacy, original_value
    ):
        if self.second_dose_date is None and date > self.first_dose_effective_date:
            return 1.0 - first_dose_efficacy
        elif date <= self.first_dose_effective_date:
            n_days = (date - self.first_dose_date).days
            return self.straight_line(
                n_days,
                p0=(0, original_value),
                p1=(self.first_dose_effective_days, 1.0 - first_dose_efficacy),
            )
        elif self.first_dose_effective_date <= date < self.second_dose_date:
            return 1.0 - first_dose_efficacy
        elif date < self.second_dose_effective_date:
            n_days = (date - self.second_dose_date).days
            return self.straight_line(
                n_days,
                p0=(0, 1.0 - first_dose_efficacy),
                p1=(self.second_dose_effective_days, 1.0 - second_dose_efficacy),
            )
        else:
            return 1.0 - second_dose_efficacy

    def get_updated_vaccine_effect(self, date):
        updated_susceptibility, updated_effective_multiplier = {}, {}
        for idx in self.infection_ids:
            updated_susceptibility[idx] = self.update_original_value(
                date,
                self.first_dose_sterilisation_efficacy[idx],
                self.second_dose_sterilisation_efficacy[idx],
                self.original_susceptibility.get(idx, 1.0),
            )
            updated_effective_multiplier[idx] = self.update_original_value(
                date,
                self.first_dose_symptomatic_efficacy[idx],
                self.second_dose_symptomatic_efficacy[idx],
                self.original_effective_multiplier.get(idx, 1.0),
            )
        return (updated_susceptibility, updated_effective_multiplier)


class VaccineDistribution(Policy):
    policy_type = "vaccine_distribution"

    def __init__(
        self,
        start_time: str = "2100-01-01",
        end_time: str = "2100-01-02",
        group_by: str = "age",  #'residence',
        group_type: str = "50-100",
        group_coverage: float = 1.0,
        first_dose_sterilisation_efficacy: dict = {0: 0.5},
        second_dose_sterilisation_efficacy: dict = {0: 1.0},
        first_dose_symptomatic_efficacy: dict = {0: 0.0},
        second_dose_symptomatic_efficacy: dict = {0: 0.0},
        second_dose_compliance: float = 1.0,
        mean_time_delay: int = 1,
        std_time_delay: int = 1,
        effective_after_first_dose: int = 7,
        effective_after_second_dose: int = 7,
    ):
        """
        Policy to apply a vaccinated tag to people based on certain attributes with a given probability

        Parameters
        ----------
        start_time: start time of vaccine rollout
        end_time: end time of vaccine rollout
        group_description: type of people to get the vaccine, currently support:
            by: either residence, primary activity or age
            group: group type e.g. care_home for residence or XX-YY for age range
        group_coverage: % of group to be left as having target susceptibility after vaccination
        first_dose_efficacy: % reduction in susceptibility after first dose
        second_dose_efficacy: % reduction in susceptibility after second dose
        second_dose_compliance: % of people getting their second vaccine dose if required
        mean_time_delay: mean time delay of the second dose being administered after the first dose has had an effect
        std_time_delay: std time delat of the second dose being administered
        effective_after_first_dose: number of days for the first dose to become effective
        effective_after_second_dose: number of days for second dose to become effective
        Otherwise, they will be less likely to show symptoms

        Assumptions
        -----------
        - The chance of getting your first dose in the first first_rollout_days days is uniform
        - The probability of when you get your second dose is chosen from a Gaussian distribution
          with mean mean_time_delay and std std_time_delay
        - The progression over time after vaccination (first and/or second dose) to reach the target
          susceptibilty is linear
        - The target susceptiblity after the first dose is half that of after the second dose
        - The target susceptibility after the second dose is 1-efficacy of the vaccine
        """

        super().__init__(start_time=start_time, end_time=end_time)
        self.group_attribute, self.group_value = self.process_group_description(
            group_by, group_type
        )
        self.total_days = (self.end_time - self.start_time).days
        self.group_coverage = group_coverage
        self.second_dose_compliance = second_dose_compliance
        self.mean_time_delay = mean_time_delay
        self.std_time_delay = std_time_delay
        self.effective_after_first_dose = effective_after_first_dose
        self.effective_after_second_dose = effective_after_second_dose
        self.first_dose_symptomatic_efficacy = first_dose_symptomatic_efficacy
        self.second_dose_symptomatic_efficacy = second_dose_symptomatic_efficacy
        self.first_dose_sterilisation_efficacy = first_dose_sterilisation_efficacy
        self.second_dose_sterilisation_efficacy = second_dose_sterilisation_efficacy
        self.infection_ids = list(self.first_dose_sterilisation_efficacy.keys())
        self.vaccinated_ids = set()

    def process_group_description(self, group_by, group_type):
        if group_by in ("residence", "primary_activity"):
            return f"{group_by}.group.spec", group_type
        elif group_by == "age":
            return f"{group_by}", group_type

    def is_target_group(self, person):
        if self.group_attribute != "age":
            try:
                if (
                    operator.attrgetter(self.group_attribute)(person)
                    == self.group_value
                ):
                    return True
            except:
                return False
        else:
            if (
                int(self.group_value.split("-")[0])
                <= getattr(person, self.group_attribute)
                <= int(self.group_value.split("-")[1])
            ):
                return True
        return False

    def vaccinate(self, person, date):
        person.vaccinated = True
        first_dose_effective_date = date + datetime.timedelta(
            days=self.effective_after_first_dose
        )
        # second dose
        if random() < self.second_dose_compliance:
            second_dose_lag = np.random.normal(
                loc=self.mean_time_delay, scale=self.std_time_delay
            )
            second_dose_date = first_dose_effective_date + datetime.timedelta(
                days=int(second_dose_lag)
            )
            second_dose_effective_days = self.effective_after_second_dose
        else:
            second_dose_date = None
            second_dose_effective_days = None
        person.vaccine_plan = VaccinePlan(
            first_dose_date=date,
            first_dose_effective_days=self.effective_after_first_dose,
            first_dose_symptomatic_efficacy=self.first_dose_symptomatic_efficacy,
            first_dose_sterilisation_efficacy=self.first_dose_sterilisation_efficacy,
            second_dose_date=second_dose_date,
            second_dose_effective_days=second_dose_effective_days,
            second_dose_symptomatic_efficacy=self.second_dose_symptomatic_efficacy,
            second_dose_sterilisation_efficacy=self.second_dose_sterilisation_efficacy,
            original_susceptibility=person.immunity.susceptibility_dict,
            original_effective_multiplier=person.immunity.effective_multiplier_dict,
        )
        self.vaccinated_ids.add(person.id)

    def daily_vaccine_probability(self, days_passed):
        return self.group_coverage * (
            1 / (self.total_days - days_passed * self.group_coverage)
        )

    def apply(self, person: Person, date: datetime):
        if person.should_be_vaccinated and self.is_target_group(person):
            days_passed = (date - self.start_time).days
            if random() < self.daily_vaccine_probability(days_passed=days_passed):
                self.vaccinate(person=person, date=date)

    def update_vaccine_effect(self, person, date):
        (
            updated_susceptibility,
            updated_effective_multiplier,
        ) = person.vaccine_plan.get_updated_vaccine_effect(date=date)
        for idx in person.vaccine_plan.infection_ids:
            person.immunity.susceptibility_dict[idx] = min(
                person.immunity.get_susceptibility(idx), updated_susceptibility[idx]
            )
            person.immunity.effective_multiplier_dict[idx] = min(
                person.immunity.get_effective_multiplier(idx),
                updated_effective_multiplier[idx],
            )

    def update_vaccinated(self, people, date):
        if self.vaccinated_ids:
            ids_to_remove = set()
            for pid in self.vaccinated_ids:
                person = people.get_from_id(pid)
                self.update_vaccine_effect(person=person, date=date)
                if person.vaccine_plan.is_finished(date):
                    ids_to_remove.add(person.id)
                    person.vaccine_plan = None
            self.vaccinated_ids -= ids_to_remove


class VaccineDistributions(PolicyCollection):
    policy_type = "vaccine_distribution"

    def apply(self, person: Person, date: datetime, active_policies):
        for policy in active_policies:
            policy.apply(person=person, date=date)

    def is_active(self, date: datetime):
        if self.get_active(date):
            return True
        return False

    def update_vaccinated(self, people, date: datetime):
        if self.policies:
            for policy in self.policies:
                policy.update_vaccinated(people=people, date=date)
