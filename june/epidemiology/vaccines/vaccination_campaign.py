import operator
from typing import List, Optional, Tuple, Set, TYPE_CHECKING
from random import random
import numpy as np
import datetime
import yaml
import logging
from pathlib import Path

from june import paths
from june.utils import read_date
from .vaccines import Vaccine, Vaccines

logger = logging.getLogger("vaccination")


default_config_filename = (
    paths.configs_path / "defaults/epidemiology/vaccines/vaccination_campaigns.yaml"
)
default_vaccines_config_filename = (
    paths.configs_path / "defaults/epidemiology/vaccines/vaccines.yaml"
)


# TODO:
# iii) Vaccinate individually given age, region, n doses, and vaccine type (could be made of combinations)


if TYPE_CHECKING:
    from june.demography import Person
    from june.records import Record


class VaccinationCampaign:
    """
    Defines a campaign to vaccinate a group of people in
    a given time span and with a given vaccine
    """

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
        """__init__.

        Parameters
        ----------
        vaccine : Vaccine
            vaccine to give out
        days_to_next_dose : List[int]
            days to wait from the moment a person is vaccinated to
            their next dose. Should have same length as dose_numbers
        dose_numbers : List[int]
            what doses to give out.
            Example: dose_numbers = [0,1] would give out first
            and second dose, whereas dose_numbers = [2] would
            only give a third dose
        start_time : str
            date at which to start vaccinating people
        end_time : str
            date at which to stop vaccinating people
        group_by : str
            defines what group to vaccinate.
            Examples: 'age', 'sex', 'residence', 'primary_activity'
        group_type : str
            from the group defined by group_by, what people to vaccinate.
            Examples:
            if group_by = 'age' -> group_type = '20-40' would vaccinate
            people aged between 20 and 40
            if group_by = 'residence' -> group_type = 'carehome' would vaccinate
            people living in care homes.
        group_coverage : float
            percentage of the eligible group to vaccinate. Must be between 0. and 1.
        last_dose_type : Optional[str]
            if not starting with a first dose (dose_numbers[0] = 0), whether to
            vaccinate only people whose previous vaccines where of a certain type.
        """
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
        self.days_from_administered_to_finished = (
            sum(self.days_to_next_dose)
            + sum(
                [
                    self.vaccine.days_administered_to_effective[dose]
                    for dose in self.dose_numbers
                ]
            )
            + sum(
                [
                    self.vaccine.days_effective_to_waning[dose]
                    for dose in self.dose_numbers
                ]
            )
            + sum([self.vaccine.days_waning[dose] for dose in self.dose_numbers])
        )

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
        """process_group_description.

        Parameters
        ----------
        group_by : str
            group_by
        group_type : str
            group_type

        Returns
        -------
        Tuple[str]

        """
        if group_by in ("residence", "primary_activity"):
            return f"{group_by}.group.spec", group_type
        else:
            return f"{group_by}", group_type

    def is_target_group(
        self,
        person: "Person",
    ) -> bool:
        """is_target_group.

        Parameters
        ----------
        person : "Person"
            person

        Returns
        -------
        bool

        """
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
        """has_right_dosage.

        Parameters
        ----------
        person : "Person"
            person

        Returns
        -------
        bool

        """
        if person.vaccinated is not None and self.starting_dose == 0:
            return False
        if self.starting_dose > 0:
            if person.vaccinated is None or person.vaccinated != self.starting_dose - 1:
                return False
            if self.last_dose_type and person.vaccine_type not in self.last_dose_type:
                return False
        return True

    def should_be_vaccinated(self, person: "Person") -> bool:
        """should_be_vaccinated.

        Parameters
        ----------
        person : "Person"
            person

        Returns
        -------
        bool

        """
        return self.has_right_dosage(person) and self.is_target_group(person)

    def vaccinate(
        self,
        person: "Person",
        date: datetime.datetime,
        record: Optional["Record"] = None,
    ):
        """vaccinate.

        Parameters
        ----------
        person : "Person"
            person
        date : datetime.datetime
            date
        record : Optional["Record"]
            record
        """
        vaccine_trajectory = self.vaccine.generate_trajectory(
            person=person,
            dose_numbers=self.dose_numbers,
            days_to_next_dose=self.days_to_next_dose,
            date=date,
        )
        vaccine_trajectory.update_dosage(person=person, record=record)
        person.vaccine_trajectory = vaccine_trajectory
        self.vaccinated_ids.add(person.id)

    def daily_vaccination_probability(self, days_passed: int) -> float:
        """daily_vaccination_probability.

        Parameters
        ----------
        days_passed : int
            days_passed

        Returns
        -------
        float

        """
        return self.group_coverage * (
            1 / (self.total_days - days_passed * self.group_coverage)
        )


class VaccinationCampaigns:
    """VaccinationCampaigns."""

    def __init__(self, vaccination_campaigns: List[VaccinationCampaign]):
        """__init__.

        Parameters
        ----------
        vaccination_campaigns : List[VaccinationCampaign]
            vaccination_campaigns
        """
        self.vaccination_campaigns = vaccination_campaigns

    @classmethod
    def from_config(
        cls,
        config_file: Path = default_config_filename,
        vaccines_config_file: Path = default_vaccines_config_filename,
    ):
        """from_config.

        Parameters
        ----------
        config_file : Path
            config_file
        vaccines_config_file : Path
            vaccines_config_file
        """
        vaccines = Vaccines.from_config(vaccines_config_file)
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        vaccination_campaigns = []
        for key, params_dict in config.items():
            params_dict["vaccine"] = vaccines.get_by_name(params_dict["vaccine_type"])
            vaccination_campaigns.append(
                VaccinationCampaign(
                    **{k: v for k, v in params_dict.items() if k != "vaccine_type"}
                )
            )
        return cls(
            vaccination_campaigns=vaccination_campaigns,
        )

    def __iter__(
        self,
    ):
        """__iter__."""
        return iter(self.vaccination_campaigns)

    def get_active(self, date: datetime) -> List[VaccinationCampaign]:
        """get_active.

        Parameters
        ----------
        date : datetime
            date

        Returns
        -------
        List[VaccinationCampaign]

        """
        return [vc for vc in self.vaccination_campaigns if vc.is_active(date)]

    def apply(
        self, person: "Person", date: datetime, record: Optional["Record"] = None
    ):
        """apply.

        Parameters
        ----------
        person : "Person"
            person
        date : datetime
            date
        record :
            record
        """
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

    def collect_all_dates_in_past(
        self,
        current_date: datetime.datetime,
    ) -> Set[datetime.datetime]:
        dates = set()
        for cv in self.vaccination_campaigns:
            start_time = cv.start_time
            if start_time < current_date:
                days_to_finished = cv.days_from_administered_to_finished
                end_time = min(
                    current_date,
                    cv.end_time + datetime.timedelta(days=days_to_finished),
                )
                delta = end_time - start_time
                for i in range(delta.days + 1):
                    date = start_time + datetime.timedelta(days=i)
                    dates.add(date)
        return sorted(list(dates))

    def apply_past_campaigns(
        self, people, date: datetime.datetime, record: Optional["Record"] = None
    ):
        dates_to_vaccinate = self.collect_all_dates_in_past(
            current_date=date,
        )
        for date_to_vax in dates_to_vaccinate:
            logger.info(f"Vaccinating at date {date_to_vax.date()}")
            for person in people:
                self.apply(
                    person=person,
                    date=date_to_vax,
                    record=record,
                )
                if person.vaccine_trajectory is not None:
                    person.vaccine_trajectory.update_vaccine_effect(
                        person=person, date=date_to_vax, record=record
                    )
            if record is not None:
                record.time_step(timestamp=date_to_vax)
