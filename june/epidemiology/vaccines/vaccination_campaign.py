import operator
from typing import List, Optional, Dict, Tuple
from random import random
import numpy as np
import datetime
import yaml
import logging
from pathlib import Path

from june import paths
from june.utils import read_date
from .vaccines import Vaccine

logger = logging.getLogger("vaccination")


default_config_filename = (
    paths.configs_path / "defaults/epidemiology/vaccines/vaccination_campaigns.yaml"
)
# TODO:
# i) Reformat vaccination campaign (make sure record works)
# ii) Vaccinate individually given age, region, n doses, and vaccine type (could be made of combinations)

#TODO: avoid loop people when update vaccinated to be double, do it within existing for loop

class VaccinationCampaign:
    def __init__(
        self,
        vaccine: Vaccine,
        days_to_next_dose: List[int],
        dose_numbers: List[int] = [0, 1],
        start_time: str = "2100-01-01",
        end_time: str = "2100-01-02",
        group_by: str = "age",
        group_type: str = "50-100",
        group_coverage: float = 1.0,
        last_dose_type: Optional[str] = None,
    ):
        self.start_time = read_date(start_time)
        self.end_time = read_date(end_time)
        self.vaccine = vaccine
        self.days_to_next_dose = days_to_next_dose
        self.group_attribute, self.group_value = self.process_group_description(
            group_by, group_type
        )
        self.total_days = (self.end_time - self.start_time).days
        self.group_coverage = group_coverage
        if last_dose_type is None:
            self.last_dose_type = []
        else:
            self.last_dose_type = last_dose_type
        self.dose_numbers = dose_numbers
        self.vaccinated_ids = set()
        self.starting_dose = self.dose_numbers[0]

    def is_active(self, date: datetime.datetime) -> bool:
        """
        Returns true if the policy is active, false otherwise
        Parameters
        ----------
        date:
            date to check
        """
        return self.start_time <= date < self.end_time

    def process_group_description(self, group_by: str, group_type: str) -> Tuple[str]:
        if group_by in ("residence", "primary_activity"):
            return f"{group_by}.group.spec", group_type
        else:
            return f"{group_by}", group_type

    def is_target_group(
        self,
        person: "Person",
    ) -> bool:
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

    def has_right_dosage(self, person: "Person") -> bool:
        if person.vaccinated is not None and self.starting_dose == 0:
            return False
        if self.starting_dose > 0:
            if person.vaccinated is None or person.vaccinated != self.starting_dose - 1:
                return False
            if self.last_dose_type and person.vaccine_type not in self.last_dose_type:
                return False
        return True

    def should_be_vaccinated(self, person: "Person") -> bool:
        return self.has_right_dosage(person) and self.is_target_group(person)

    def vaccinate(
        self,
        person: "Person",
        date: datetime.datetime,
        record: Optional["Record"] = None,
    ):
        person.vaccine_trajectory = self.vaccine.generate_trajectory(
            person=person,
            dose_numbers=self.dose_numbers,
            days_to_next_dose=self.days_to_next_dose,
            date=date,
        )
        self.update_dosage(person=person, record=record)
        self.vaccinated_ids.add(person.id)

    def daily_vaccination_probability(self, days_passed: int) -> float:
        return self.group_coverage * (
            1 / (self.total_days - days_passed * self.group_coverage)
        )

    def update_dosage(
        self,
        person,
        record=None,
    ):
        dose_number = person.vaccine_trajectory.current_dose
        person.vaccinated = dose_number
        person.vaccine_type = self.vaccine.name
        if record is not None:
            record.events["vaccines"].accumulate(
                person.id,
                self.vaccine.name,
                dose_number,
            )

    def update_vaccine_effect(
        self,
        person: "Person",
        date: datetime.datetime,
        record=None,
    ):
        trajectory = person.vaccine_trajectory
        immunity = person.immunity
        dose_number = trajectory.current_dose
        # update person.vaccinated here and use record
        for infection_id in self.vaccine.infection_ids:
            updated_susceptibility = trajectory.susceptibility(
                date=date, infection_id=infection_id
            )
            updated_effective_multiplier = trajectory.effective_multiplier(
                date=date, infection_id=infection_id
            )
            immunity.susceptibility_dict[infection_id] = min(
                trajectory.prior_susceptibility.get(infection_id, 1.0),
                updated_susceptibility,
            )
            immunity.effective_multiplier_dict[infection_id] = min(
                trajectory.prior_effective_multiplier.get(infection_id, 1.0),
                updated_effective_multiplier,
            )
            if trajectory.current_dose != dose_number:
                self.update_dosage(person=person, record=record)
        trajectory.update_trajectory_stage(date=date)



class VaccinationCampaigns:
    def __init__(self, vaccination_campaigns: List[VaccinationCampaign]):
        self.vaccination_campaigns = vaccination_campaigns

    @classmethod
    def from_config(
        cls,
        config_file: Path = default_config_filename,
    ):
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        vaccination_campaigns = []
        for key, value in config.items():
            vaccination_campaigns.append(VaccinationCampaign(**value))
        return cls(
            vaccination_campaigns=vaccination_campaigns,
        )

    def __iter__(
        self,
    ):
        return iter(self.vaccination_campaigns)

    def update_vaccinated(
        self,
        people: "Population",
        date: datetime.datetime,
        record: Optional[Record] = None,
    ):
        for cv in self.vaccination_campaigns:
            cv.update_vaccinated(
                people=people,
                date=date,
                record=record,
            )

    def get_active(self, date: datetime) -> List[VaccinationCampaign]:
        return [vc for vc in self.vaccination_campaigns if vc.is_active(date)]

    def apply(self, person: "Person", date: datetime, record=None):
        active_campaigns = self.get_active(date=date)
        daily_probability, campaigns_to_chose_from = [], []
        for vc in active_campaigns:
            if vc.should_be_vaccinated(
                person=person,
            ):
                days_passed = (date - vc.start_time).days
                daily_probability.append(
                    vc.daily_vaccination_probability(days_passed=days_passed)
                )
                campaigns_to_chose_from.append(vc)
        daily_probability = np.array(daily_probability)
        norm = daily_probability.sum()
        if norm > 0.0:
            if random() < norm:
                daily_probability /= norm
                campaign = np.random.choice(
                    campaigns_to_chose_from, p=daily_probability
                )
                campaign.vaccinate(person=person, date=date, record=record)
