import operator
from typing import List, Optional
from random import random
import numpy as np
import datetime
import logging

from june.demography.person import Person
from .policy import Policy, PolicyCollection
from .vaccines import Vaccine


logger = logging.getLogger("vaccination")


# TODO: Combine stagesgenerator and vaccinetrajectory into one object
# TODO: Group coverage should be given by stage to model complacency
# TODO: Smearing of dates (give mean and std and generate spacing between doses)
# TODO: Generalize to varying functional forms for waning, with extra params


class VaccineStage:

    valid_efficacy_types = ("symptomatic", "sterilisation")

    def __init__(
        self,
        date_administered: datetime.datetime,
        days_to_effective: int,
        sterilisation_efficacy: dict,
        symptomatic_efficacy: dict,
        prior_sterilisation_efficacy: dict = None,
        prior_symptomatic_efficacy: dict = None,
    ):
        """
        A stage of a vaccination trajectory.
        Dictionaries map infection ids to their respective vax efficacies.

        Parameters
        ----------
        date_administered:
            date the stage begins
        days_to_effective:
            number of days since administered day for the stage to be fully effective
        sterilisation_efficacy
            final full efficacy against infection
        symptomatic_efficacy
            final full efficacy against symptoms
        prior_sterilisation_efficacy
            prior sterlisiation efficacy, between the date administered and the final effective date,
            the efficacy varies linearly between prior and final.
        prior_symptomatic_efficacy
            prior symptomatic efficacy, between the date administered and the final effective date,
            the efficacy varies linearly between prior and final.
        """
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
        self.administered = False

    def get_vaccine_efficacy(
        self,
        date,
        efficacy_type: str,
        infection_id: int,
    ):
        if efficacy_type not in self.valid_efficacy_types:
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
    def __init__(self, vaccine, days_to_next_dose):
        self.vaccine = vaccine
        self.days_to_next_dose = days_to_next_dose

    def __call__(
        self,
        person,
        date_administered: datetime.datetime,
    ):
        prior_susceptibility = person.immunity.susceptibility_dict
        prior_effective_multiplier = person.immunity.effective_multiplier_dict
        prior_sterilisation_efficacy = {
            k: 1 - prior_susceptibility.get(k, 1.0)
            for k, v in self.vaccine.sterilisation_efficacies[0].items()
        }
        prior_symptomatic_efficacy = {
            k: 1 - prior_effective_multiplier.get(k, 1.0)
            for k, v in self.vaccine.symptomatic_efficacies[0].items()
        }
        stages = []
        for dose_number in self.vaccine.doses:
            i = dose_number - self.vaccine.doses[0]
            days = self.days_to_next_dose[i]
            date = date_administered + datetime.timedelta(days=days)
            (
                sterilisation_efficacy,
                symptomatic_efficacy,
            ) = self.vaccine.get_efficacy_for_dose_person(
                person=person, dose=dose_number
            )
            stage = VaccineStage(
                date_administered=date,
                days_to_effective=self.vaccine.days_to_effective[i],
                sterilisation_efficacy=sterilisation_efficacy,
                symptomatic_efficacy=symptomatic_efficacy,
                prior_sterilisation_efficacy=prior_sterilisation_efficacy,
                prior_symptomatic_efficacy=prior_symptomatic_efficacy,
            )
            prior_sterilisation_efficacy = sterilisation_efficacy
            prior_symptomatic_efficacy = symptomatic_efficacy
            stages.append(stage)
        return stages


class VaccineTrajectory:
    def __init__(
        self,
        person,
        date_administered,
        vaccine: "Vaccine",
        days_to_next_dose,
    ):
        stage_generator = VaccineStagesGenerator(
            vaccine=vaccine,
            days_to_next_dose=days_to_next_dose,
        )
        stages = stage_generator(person=person, date_administered=date_administered)
        self.stages = sorted(stages, key=operator.attrgetter("date_administered"))
        self.stage_days = [
            (stage.date_administered - date_administered).days for stage in self.stages
        ]
        self.prior_susceptibility = person.immunity.susceptibility_dict
        self.prior_effective_multiplier = person.immunity.effective_multiplier_dict
        self.doses = vaccine.doses
        self.vaccine_name = vaccine.name

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
        index_stage = self.get_dose_number(date=date) - self.doses[0]
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

    def get_stage_index(
        self,
        date: datetime.datetime,
    ):
        days_from_start = (date - self.stages[0].date_administered).days
        return min(
            np.searchsorted(self.stage_days, days_from_start, side="right") - 1,
            len(self.stages) - 1,
        )

    def get_dose_number(
        self,
        date: datetime.datetime,
    ):
        index_stage = self.get_stage_index(date=date)
        return self.doses[index_stage]

    def is_date_dose(self, date):
        dose_number = self.get_dose_number(date=date)
        stage_idx = dose_number - self.doses[0]
        if not self.stages[stage_idx].administered:
            return date.date() == self.stages[stage_idx].date_administered.date()
        return False

    def give_dose(self, person, date, record):
        stage_index = self.get_stage_index(date=date)
        self.stages[stage_index].administered = True
        dose_number = person.vaccine_trajectory.doses[stage_index]
        person.vaccinated = dose_number
        person.vaccine_type = self.vaccine_name
        if record is not None:
            record.events["vaccines"].accumulate(
                person.id,
                self.vaccine_name,
                dose_number,
            )


class VaccineDistribution(Policy):
    policy_type = "vaccine_distribution"

    def __init__(
        self,
        vaccine_type: "str",
        days_to_next_dose: List[int],
        doses: List[int] = [0, 1],
        start_time: str = "2100-01-01",
        end_time: str = "2100-01-02",
        group_by: str = "age",  # 'residence',
        group_type: str = "50-100",
        group_coverage: float = 1.0,
        last_dose_type: Optional[str] = None,
    ):
        """
         Policy to distribute vaccines among a population

         Parameters
         ----------
         days_to_next_dose: list of integers with the days between doses.
         (It'd normally start with 0 since the first dose happens on the first date)
        start_time: start time of vaccine rollout
         end_time: end time of vaccine rollout
         group_description: type of people to get the vaccine, currently support:
             by: either residence, primary activity or age
             group: group type e.g. care_home for residence or XX-YY for age range
         group_coverage: % of group to be left as having target susceptibility after vaccination

         Assumptions
         -----------
         - The chance of getting your first dose in the first first_rollout_days days is uniform
         - The target susceptibility after the first dose is half that of after the second dose
         - The target susceptibility after the second dose is 1-efficacy of the vaccine
        """

        super().__init__(start_time=start_time, end_time=end_time)
        self.vaccine = Vaccine.from_config(vaccine_type=vaccine_type, doses=doses)
        self.days_to_next_dose = days_to_next_dose
        self.group_attribute, self.group_value = self.process_group_description(
            group_by, group_type
        )
        self.total_days = (self.end_time - self.start_time).days
        self.group_coverage = group_coverage
        self.infection_ids = self._read_infection_ids(
            self.vaccine.sterilisation_efficacies
        )
        if last_dose_type is None:
            self.last_dose_type = []
        else:
            self.last_dose_type = last_dose_type
        self.vaccinated_ids = set()

    def _read_infection_ids(self, sterilisation_efficacies):
        ids = set()
        for dd in sterilisation_efficacies:
            for key in dd:
                ids.add(key)
        return list(ids)

    def process_group_description(self, group_by, group_type):
        if group_by in ("residence", "primary_activity"):
            return f"{group_by}.group.spec", group_type
        elif group_by == "age":
            return f"{group_by}", group_type

    def is_target_group(
        self,
        person,
    ):
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
                < int(self.group_value.split("-")[1])
            ):
                return True
        return False

    def should_be_vaccinated(self, person):
        starting_dose = self.vaccine.doses[0]
        if person.vaccinated is not None and starting_dose == 0:
            return False
        if starting_dose > 0 and (
            person.vaccinated is None or person.vaccinated != starting_dose - 1
        ):
            return False
        if (
            self.last_dose_type
            and starting_dose > 0
            and person.vaccine_type not in self.last_dose_type
        ):
            return False
        return True

    def vaccinate(self, person, date, record):
        person.vaccine_trajectory = VaccineTrajectory(
            person=person,
            date_administered=date,
            vaccine=self.vaccine,
            days_to_next_dose=self.days_to_next_dose,
        )
        person.vaccine_trajectory.give_dose(
            person=person,
            date=date,
            record=record,
        )
        self.vaccinated_ids.add(person.id)

    def daily_vaccine_probability(self, days_passed):
        return self.group_coverage * (
            1 / (self.total_days - days_passed * self.group_coverage)
        )

    def apply(self, person: Person, date: datetime, record=None):
        if (
            self.should_be_vaccinated(
                person,
            )
            and self.is_target_group(person)
        ):

            days_passed = (date - self.start_time).days
            if random() < self.daily_vaccine_probability(days_passed=days_passed):
                self.vaccinate(person=person, date=date, record=record)

    def update_vaccine_effect(self, person, date, record=None):
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
        if person.vaccine_trajectory.is_date_dose(date=date):
            person.vaccine_trajectory.give_dose(
                person=person,
                date=date,
                record=record,
            )

    def update_vaccinated(self, people, date, record=None):
        if self.vaccinated_ids:
            ids_to_remove = set()
            for pid in self.vaccinated_ids:
                person = people.get_from_id(pid)
                if person.vaccine_trajectory is not None:
                    self.update_vaccine_effect(person=person, date=date, record=record)
                    if person.vaccine_trajectory.is_finished(date):
                        ids_to_remove.add(person.id)
                        person.vaccine_trajectory = None
            self.vaccinated_ids -= ids_to_remove

    def _apply_past_vaccinations(self, people, date, record=None):
        date = min(date, self.end_time)
        days_in_the_past = max(0, (date - self.start_time).days)
        if days_in_the_past > 0:
            for i in range(days_in_the_past):
                date_to_vax = self.start_time + datetime.timedelta(days=i)
                logger.info(f"Vaccinating at date {date_to_vax.date()}")
                for person in people:
                    self.apply(person=person, date=date_to_vax, record=record)

    def initialize(self, world, date, record=None):
        """
        Initializes policy, vaccinating people in the past if needed.
        """
        return self._apply_past_vaccinations(
            people=world.people, date=date, record=record
        )


class VaccineDistributions(PolicyCollection):
    policy_type = "vaccine_distribution"

    def apply(self, person: Person, date: datetime, active_policies: List, record):
        for policy in active_policies:
            policy.apply(person=person, date=date, record=record)

    def is_active(self, date: datetime):
        if self.get_active(date):
            return True
        return False

    def update_vaccinated(self, people, date: datetime, record):
        if self.policies:
            for policy in self.policies:
                policy.update_vaccinated(people=people, date=date, record=record)
