import operator
from typing import List, Dict
from random import random
import numpy as np
import datetime
from june.demography.person import Person
from .policy import Policy, PolicyCollection


class VaccineStage:
    def __init__(
        self,
        date_administered: datetime.datetime,
        days_to_effective: int,
        sterilisation_efficacy: dict,
        symptomatic_efficacy: dict,
        prior_sterilisation_efficacy: dict = None,
        prior_symptomatic_efficacy: dict = None,
    ):
        self.date_administered = date_administered
        self.days_to_effective = days_to_effective
        self.sterilisation_efficacy = sterilisation_efficacy
        self.symptomatic_efficacy = symptomatic_efficacy
        self.effective_date = self.date_administered + datetime.timedelta(
            days=self.days_to_effective
        )
        if not prior_sterilisation_efficacy:
            self.prior_sterilisation_efficacy = {k: 0.0 for k in sterilisation_efficacy}
        else:
            self.prior_sterilisation_efficacy = prior_sterilisation_efficacy
        if not prior_symptomatic_efficacy:
            self.prior_symptomatic_efficacy = {k: 0.0 for k in symptomatic_efficacy}
        else:
            self.prior_symptomatic_efficacy = prior_symptomatic_efficacy

    # TODO: Generalize to varying functional forms for waning, with extra
    # parameters
    def get_vaccine_efficacy(
        self,
        date,
        efficacy_type: str,
        infection_id: int,
    ):
        if efficacy_type not in ("symptomatic", "sterilisation"):
            raise ValueError
        prior_value = getattr(self, f"prior_{efficacy_type}_efficacy")[infection_id]
        efficacy = getattr(self, f"{efficacy_type}_efficacy")[infection_id]
        if date < self.effective_date:
            n_days = (date - self.date_administered).days
            m = (efficacy - prior_value) / self.days_to_effective
            n = prior_value
            return m * n_days + n
        return efficacy


class VaccineStagesGenerator:
    def __init__(
        self,
        days_to_next_dose: List[int],
        days_to_effective: List[int],
        sterilisation_efficacies: List[Dict],
        symptomatic_efficacies: List[Dict],
    ):
        self.days_to_next_dose = days_to_next_dose
        self.days_to_effective = days_to_effective
        self.sterilisation_efficacies = sterilisation_efficacies
        self.symptomatic_efficacies = symptomatic_efficacies

    def __call__(
        self,
        person,
        date_administered: datetime.datetime,
    ):
        prior_susceptibility = person.immunity.susceptibility_dict
        prior_effective_multiplier = person.immunity.effective_multiplier_dict
        prior_sterilisation_efficacy = {
            k: 1 - prior_susceptibility.get(k, 1.0)
            for k, v in self.sterilisation_efficacies[0].items()
        }
        prior_symptomatic_efficacy = {
            k: 1 - prior_effective_multiplier.get(k, 1.0)
            for k, v in self.symptomatic_efficacies[0].items()
        }
        stages = []
        for i, days in enumerate(self.days_to_next_dose):
            date = date_administered + datetime.timedelta(days=days)
            stage = VaccineStage(
                date_administered=date,
                days_to_effective=self.days_to_effective[i],
                sterilisation_efficacy=self.sterilisation_efficacies[i],
                symptomatic_efficacy=self.symptomatic_efficacies[i],
                prior_sterilisation_efficacy=prior_sterilisation_efficacy,
                prior_symptomatic_efficacy=prior_symptomatic_efficacy,
            )
            prior_sterilisation_efficacy = self.sterilisation_efficacies[i]
            prior_symptomatic_efficacy = self.symptomatic_efficacies[i]
            stages.append(stage)
        return stages


#TODO: COMBINE STAGEGENERATOR AND TRAJECTORY
class VaccineTrajectory:
    def __init__(
        self,
        person,
        date_administered,
        days_to_next_dose: List[int],
        days_to_effective: List[int],
        sterilisation_efficacies: List[Dict],
        symptomatic_efficacies: List[Dict],
    ):
        stage_generator = VaccineStagesGenerator(
                days_to_next_dose= days_to_next_dose,
                days_to_effective = days_to_effective,
                sterilisation_efficacies=sterilisation_efficacies,
                symptomatic_efficacies = symptomatic_efficacies,
        )
        stages = stage_generator(person=person, date_administered=date_administered)
        self.stages = sorted(stages, key=operator.attrgetter("date_administered"))
        self.stage_days = [
            (stage.date_administered - date_administered).days for stage in self.stages
        ]
        self.prior_susceptibility = person.immunity.susceptibility_dict
        self.prior_effective_multiplier = person.immunity.effective_multiplier_dict



    def susceptibility(self, date, infection_id: int):
        return 1.0 - self.get_vaccine_efficacy(
            date=date, efficacy_type="sterilisation", infection_id=infection_id
        )

    def effective_multiplier(self, date, infection_id: int):
        return 1.0 - self.get_vaccine_efficacy(
            date=date, efficacy_type="symptomatic", infection_id=infection_id
        )

    def get_vaccine_efficacy(
        self,
        date,
        efficacy_type: str,
        infection_id: int,
    ):
        days_from_start = (date - self.stages[0].date_administered).days
        index_stage = min(
            np.searchsorted(self.stage_days, days_from_start, side="right") - 1,
            len(self.stages) - 1,
        )
        stage = self.stages[index_stage]
        return stage.get_vaccine_efficacy(
            date=date, efficacy_type=efficacy_type, infection_id=infection_id
        )

    def is_finished(
        self,
        date: datetime.datetime,
    ):
        if date > self.stages[-1].effective_date:
            return True
        return False


# TODO: Group coverage should be given by stage
class VaccineDistribution(Policy):
    policy_type = "vaccine_distribution"

    def __init__(
        self,
        days_to_next_dose: List[int],
        days_to_effective: List[int],
        sterilisation_efficacies: List[Dict],
        symptomatic_efficacies: List[Dict],
        infection_ids: List[int],
        start_time: str = "2100-01-01",
        end_time: str = "2100-01-02",
        group_by: str = "age",  # 'residence',
        group_type: str = "50-100",
        group_coverage: float = 1.0,
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
        self.days_to_next_dose = days_to_next_dose
        self.days_to_effective = days_to_effective
        self.sterilisation_efficacies = sterilisation_efficacies
        self.symptomatic_efficacies = symptomatic_efficacies
        self.group_attribute, self.group_value = self.process_group_description(
            group_by, group_type
        )
        self.total_days = (self.end_time - self.start_time).days
        self.group_coverage = group_coverage
        self.infection_ids = infection_ids
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
            except Exception:
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
        # TODO: implement varying compliance per step
        person.vaccinated = True
        person.vaccine_trajectory = VaccineTrajectory(
                person=person,
                date_administered=date,
                days_to_next_dose = self.days_to_next_dose,
                days_to_effective = self.days_to_effective,
                sterilisation_efficacies = self.sterilisation_efficacies,
                symptomatic_efficacies=self.symptomatic_efficacies,
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
        for infection_id in self.infection_ids:
            updated_susceptibility = person.vaccine_trajectory.susceptibility(
                date=date, infection_id=infection_id
            )
            updated_effective_multiplier = (
                person.vaccine_trajectory.effective_multiplier(
                    date=date, infection_id=infection_id
                )
            )
            person.immunity.susceptibility_dict[infection_id] = min(
                person.vaccine_trajectory.prior_susceptibility.get(infection_id, 1.0),
                updated_susceptibility,
            )
            person.immunity.effective_multiplier_dict[infection_id] = min(
                person.vaccine_trajectory.prior_effective_multiplier.get(
                    infection_id, 1.0
                ),
                updated_effective_multiplier,
            )

    def update_vaccinated(self, people, date):
        if self.vaccinated_ids:
            ids_to_remove = set()
            for pid in self.vaccinated_ids:
                person = people.get_from_id(pid)
                self.update_vaccine_effect(person=person, date=date)
                if person.vaccine_trajectory.is_finished(date):
                    ids_to_remove.add(person.id)
                    person.vaccine_trajectory = None
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
