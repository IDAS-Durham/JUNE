import yaml
import operator
from pathlib import Path
import datetime
from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
import numpy as np

from june import paths
from june.epidemiology.infection import infection as infection_module
from june.epidemiology.infection.disease_config import DiseaseConfig
from june.utils.parse_probabilities import parse_age_probabilities


# TODO: apply doses from file
# Start with (date, pseudo_id, region, age, dose, vaccine_type)
# (person id, dose number, vaccine type) -> append to trajectory.doses

if TYPE_CHECKING:
    from june.demography import Person


@dataclass
class Efficacy:
    """Efficacy types"""

    infection: Dict[int, float]
    symptoms: Dict[int, float]
    waning_factor: float

    def __call__(self, protection_type: str, infection_id: int):
        """__call__.

        Parameters
        ----------
        protection_type : str
            protection_type
        infection_id : int
            infection_id
        """
        return getattr(self, f"{protection_type}").get(infection_id)

    def __mul__(self, factor: float):
        """__mul__.

        Parameters
        ----------
        factor : float
            factor
        """
        return Efficacy(
            infection={k: v * factor for k, v in self.infection.items()},
            symptoms={k: v * factor for k, v in self.symptoms.items()},
            waning_factor=1.0,
        )


class Dose:
    """Dose."""

    def __init__(
        self,
        number: int,
        date_administered: datetime.datetime,
        days_administered_to_effective: int,
        days_effective_to_waning: int,
        days_waning: int,
        prior_efficacy: Efficacy,
        efficacy: Efficacy,
    ):
        """__init__.

        Parameters
        ----------
        number : int
            number
        date_administered : datetime.datetime
            date_administered
        days_administered_to_effective : int
            days_administered_to_effective
        days_effective_to_waning : int
            days_effective_to_waning
        days_waning : int
            days_waning
        prior_efficacy : Efficacy
            prior_efficacy
        efficacy : Efficacy
            efficacy
        """
        self.number = number
        self.days_administered_to_effective = days_administered_to_effective
        self.days_effective_to_waning = days_effective_to_waning
        self.days_waning = days_waning
        self.efficacy = efficacy
        self.prior_efficacy = prior_efficacy
        self.date_administered = date_administered
        self.date_effective = self.date_administered + datetime.timedelta(
            days=self.days_administered_to_effective
        )
        self.date_waning = self.date_administered + datetime.timedelta(
            days=self.days_effective_to_waning + self.days_administered_to_effective
        )
        self.date_finished = self.date_administered + datetime.timedelta(
            days=self.days_waning
            + self.days_effective_to_waning
            + self.days_administered_to_effective
        )

    def get_efficacy(
        self, date: datetime.datetime, infection_id: int, protection_type: str
    ):
        """get_efficacy.

        Parameters
        ----------
        date : datetime.datetime
            date
        infection_id : int
            infection_id
        protection_type : str
            protection_type
        """
        efficacy = self.efficacy(
            protection_type=protection_type, infection_id=infection_id
        )
        if date > self.date_finished:
            return self.efficacy.waning_factor * self.efficacy(
                protection_type=protection_type, infection_id=infection_id
            )

        elif date > self.date_waning:
            prior_efficacy = efficacy
            final_efficacy = self.efficacy.waning_factor * self.efficacy(
                protection_type=protection_type, infection_id=infection_id
            )
            prior_date = self.date_waning
            duration = self.days_waning
        elif date > self.date_effective:
            return efficacy
        elif date >= self.date_administered:
            prior_efficacy = self.prior_efficacy(
                protection_type=protection_type, infection_id=infection_id
            )
            final_efficacy = efficacy
            prior_date = self.date_administered
            duration = self.days_administered_to_effective
        n_days = (date - prior_date).days
        m = (final_efficacy - prior_efficacy) / duration
        n = prior_efficacy
        return m * n_days + n


class VaccineTrajectory:
    """VaccineTrajectory."""

    def __init__(self, doses: List[Dose], name: str, infection_ids: List[int]):
        """__init__.

        Parameters
        ----------
        doses : List[Dose]
            doses
        name : str
            name
        infection_ids : List[int]
            infection_ids
        """
        self.doses = sorted(doses, key=operator.attrgetter("date_administered"))
        self.name = name
        self.infection_ids = infection_ids
        self.first_dose_date = self.doses[0].date_administered
        self.dates_administered = [
            (dose.date_administered - self.first_dose_date).days for dose in self.doses
        ]
        (
            self.prior_susceptibility,
            self.prior_effective_multiplier,
        ) = self._get_immunity_prior_to_trajectory()
        self.stage = 0

    @property
    def current_dose(
        self,
    ):
        """current_dose."""
        return self.doses[self.stage].number

    def _get_immunity_prior_to_trajectory(
        self,
    ):
        """_get_immunity_prior_to_trajectory."""
        prior_efficacy = self.doses[0].prior_efficacy
        suscepbitility = {
            inf_id: 1 - value for inf_id, value in prior_efficacy.infection.items()
        }
        effective_multiplier = {
            inf_id: 1 - value for inf_id, value in prior_efficacy.symptoms.items()
        }
        return suscepbitility, effective_multiplier

    def get_dose_index(self, date: datetime.datetime):
        """get_dose_index.

        Parameters
        ----------
        date : datetime.datetime
            date
        """
        days_from_start = (date - self.first_dose_date).days
        return min(
            np.searchsorted(self.dates_administered, days_from_start, side="right") - 1,
            len(self.doses) - 1,
        )

    def get_dose_number(self, date: datetime.datetime):
        """get_dose_number.

        Parameters
        ----------
        date : datetime.datetime
            date
        """
        return self.doses[self.get_dose_index(date=date)].number

    def update_trajectory_stage(self, date: datetime.datetime):
        """update_trajectory_stage.

        Parameters
        ----------
        date : datetime.datetime
            date
        """
        if (
            self.stage < len(self.doses) - 1
            and date >= self.doses[self.stage + 1].date_administered
        ):
            self.stage += 1
            self.dose_number = self.doses[self.stage].number

    def get_efficacy(
        self, date: datetime.datetime, infection_id: int, protection_type: str
    ):
        """get_efficacy.

        Parameters
        ----------
        date : datetime.datetime
            date
        infection_id : int
            infection_id
        protection_type : str
            protection_type
        """
        return self.doses[self.stage].get_efficacy(
            date=date, infection_id=infection_id, protection_type=protection_type
        )

    def susceptibility(self, date: datetime.datetime, infection_id: int):
        """susceptibility.

        Parameters
        ----------
        date : datetime.datetime
            date
        infection_id : int
            infection_id
        """
        return 1.0 - self.get_efficacy(
            date=date, protection_type="infection", infection_id=infection_id
        )

    def effective_multiplier(self, date, infection_id: int):
        """effective_multiplier.

        Parameters
        ----------
        date :
            date
        infection_id : int
            infection_id
        """
        return 1.0 - self.get_efficacy(
            date=date, protection_type="symptoms", infection_id=infection_id
        )

    def is_finished(self, date):
        """is_finished.

        Parameters
        ----------
        date :
            date
        """
        if date > self.doses[-1].date_finished:
            return True
        return False

    def update_dosage(self, person, entered_via, record=None):
        """update_dosage.

        Parameters
        ----------
        person :
            person
        record :
            record
        """

        dose_number = self.current_dose
        person.vaccinated = dose_number
        person.vaccine_type = self.name
        if record is not None:
            record.events["vaccines"].accumulate(person.id, self.name, dose_number)
        if entered_via == 1:
            import sys
            #sys.exit()
        #print(f"DOSAGE UPDATED for {person.id}!")

    def update_vaccine_effect(
        self, person: "Person", date: datetime.datetime, record=None
    ):
        """update_vaccine_effect.

        Parameters
        ----------
        person : "Person"
            person
        date : datetime.datetime
            date
        record :
            record
        """
        if self.is_finished(date=date):
            #print(f"Person {person.id} has finished their vaccine trajectory.")
            person.vaccine_trajectory = None
            return
        immunity = person.immunity
        dose_number = self.current_dose
        # update person.vaccinated here and use record
        self.update_trajectory_stage(date=date)
        #print(f"Person ID: {person.id}")
        for infection_id in self.infection_ids:
            # Compute updated susceptibility and effective multiplier
            updated_susceptibility = self.susceptibility(
                date=date, infection_id=infection_id
            )
            updated_effective_multiplier = self.effective_multiplier(
                date=date, infection_id=infection_id
            )

            # Debugging print statements for intermediate values
            #print(f"Infection ID: {infection_id}")
            #print(f"  Updated Susceptibility: {updated_susceptibility}")
            #print(f"  Updated Effective Multiplier: {updated_effective_multiplier}")

            # Compute new values for susceptibility_dict and effective_multiplier_dict
            prior_susceptibility = self.prior_susceptibility.get(infection_id, 1.0)
            prior_effective_multiplier = self.prior_effective_multiplier.get(infection_id, 1.0)

            immunity.susceptibility_dict[infection_id] = min(
                prior_susceptibility, updated_susceptibility
            )
            immunity.effective_multiplier_dict[infection_id] = min(
                prior_effective_multiplier, updated_effective_multiplier,
            )

            # Debugging print statements for final values
            #print(f"  Prior Susceptibility: {prior_susceptibility}")
            #print(f"  Final Susceptibility: {immunity.susceptibility_dict[infection_id]}")
            #print(f"  Prior Effective Multiplier: {prior_effective_multiplier}")
            #print(
            #    f"  Final Effective Multiplier: {immunity.effective_multiplier_dict[infection_id]}"
            #)
        if self.current_dose != dose_number:
            #print(f"\nDOSAGE about to be updated via UPDATE_VACCINE_EFFECT for {person.id}:")
            self.update_dosage(person=person, record=record, entered_via=1)
        


class Vaccine:
    """Vaccine."""

    def __init__(
        self,
        name: str,
        days_administered_to_effective: List[int],
        days_effective_to_waning: List[int],
        days_waning: List[int],
        sterilisation_efficacies,
        symptomatic_efficacies,
        waning_factor: Optional[float] = 1.0,
    ):
        """
        Class defining a vaccine type and its effectiveness

        Parameters
        ----------
        name:
           vaccine name
        days_to_effective:
            number of days it takes for current dose to be fully effective
        sterilisation_efficacy
            final full efficacy against infection, by variant and age
        symptomatic_efficacy
            final full efficacy against symptoms, by variant and age
        """

        self.name = name
        self.days_administered_to_effective = days_administered_to_effective
        self.days_effective_to_waning = days_effective_to_waning
        self.days_waning = days_waning
        self.sterilisation_efficacies = self._parse_efficacies(sterilisation_efficacies)
        self.symptomatic_efficacies = self._parse_efficacies(symptomatic_efficacies)
        self.infection_ids = self._read_infection_ids(self.sterilisation_efficacies)
        self.waning_factor = waning_factor


    @classmethod
    def from_dict(cls, name, data):
        """
        Create a Vaccine instance from a dictionary.

        Parameters
        ----------
        name : str
            The name of the vaccine.
        data : dict
            Dictionary containing vaccine attributes.

        Returns
        -------
        Vaccine
            The initialized Vaccine object.
        """
        return cls(
            name=name,
            days_administered_to_effective=data.get("days_administered_to_effective", []),
            days_effective_to_waning=data.get("days_effective_to_waning", []),
            days_waning=data.get("days_waning", []),
            waning_factor=data.get("waning_factor", 1.0),
            sterilisation_efficacies=data.get("sterilisation_efficacies", []),
            symptomatic_efficacies=data.get("symptomatic_efficacies", []),
        )
    @classmethod
    def from_config_dict(cls, name: str, config: Dict):
        """from_config_dict.

        Parameters
        ----------
        name : str
            name
        config : Dict
            config
        """
        return cls(
            name=name,
            days_administered_to_effective=config["days_administered_to_effective"],
            days_effective_to_waning=config["days_effective_to_waning"],
            days_waning=config["days_waning"],
            sterilisation_efficacies=config["sterilisation_efficacies"],
            symptomatic_efficacies=config["symptomatic_efficacies"],
            waning_factor=config["waning_factor"],
        )

    '''    
    @classmethod
    def from_config(
        cls, vaccine_type: str, config_file: Path = default_config_filename
    ):
        """from_config.

        Parameters
        ----------
        vaccine_type : str
            vaccine_type
        config_file : Path
            config_file
        """
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        config = config[vaccine_type]
        return cls.from_config_dict(name=vaccine_type, config=config) '''

    def _read_infection_ids(self, sterilisation_efficacies):
        """_read_infection_ids.

        Parameters
        ----------
        sterilisation_efficacies :
            sterilisation_efficacies
        """
        ids = set()
        for dd in sterilisation_efficacies:
            for key in dd:
                ids.add(key)
        return list(ids)

    def _parse_efficacies(self, efficacies):
        """_parse_efficacies.

        Parameters
        ----------
        efficacies :
            efficacies
        """
        ret = []
        for dd in efficacies:
            dd_id = {}
            for key in dd:
                infection_id = getattr(infection_module, key).infection_id()
                dd_id[infection_id] = parse_age_probabilities(dd[key])
            ret.append(dd_id)
        return ret

    def collect_prior_efficacy(self, person):
        """collect_prior_efficacy.

        Parameters
        ----------
        person :
            person
        """
        immunity = person.immunity
        return Efficacy(
            infection={
                inf_id: 1.0 - immunity.susceptibility_dict.get(inf_id, 1.0)
                for inf_id in self.infection_ids
            },
            symptoms={
                inf_id: 1.0 - immunity.effective_multiplier_dict.get(inf_id, 1.0)
                for inf_id in self.infection_ids
            },
            waning_factor=1.0,
        )

    def generate_trajectory(
        self,
        person: "Person",
        dose_numbers: List[int],
        days_to_next_dose: List[int],
        date: datetime.datetime,
    ) -> VaccineTrajectory:
        """generate_trajectory.

        Parameters
        ----------
        person : "Person"
            person
        dose_numbers : List[int]
            dose_numbers
        days_to_next_dose : List[int]
            days_to_next_dose
        date : datetime.datetime
            date

        Returns
        -------
        VaccineTrajectory

        """
        #print(f"\n=== Generating Vaccine Trajectory for Person ID: {person.id} ===")
        prior_efficacy = self.collect_prior_efficacy(person=person)
        #print(f"Initial Prior Efficacy: {prior_efficacy}")

        doses = []
        for i, dose in enumerate(dose_numbers):
            date += datetime.timedelta(days=days_to_next_dose[i])
            #print(f"\nDose {dose}:")
            #print(f"  Date Administered: {date.strftime('%Y-%m-%d')}")

            efficacy = Efficacy(
                infection={
                    inf_id: self.sterilisation_efficacies[dose][inf_id][person.age]
                    for inf_id in self.infection_ids
                },
                symptoms={
                    inf_id: self.symptomatic_efficacies[dose][inf_id][person.age]
                    for inf_id in self.infection_ids
                },
                waning_factor=self.waning_factor,
            )
            #print(f"  Efficacy (Infection): {efficacy.infection}")
            #print(f"  Efficacy (Symptoms): {efficacy.symptoms}")
            #print(f"  Waning Factor: {efficacy.waning_factor}")

            doses.append(
                Dose(
                    number=dose,
                    date_administered=date,
                    days_administered_to_effective=self.days_administered_to_effective[
                        dose
                    ],
                    days_effective_to_waning=self.days_effective_to_waning[dose],
                    days_waning=self.days_waning[dose],
                    prior_efficacy=prior_efficacy,
                    efficacy=efficacy,
                )
            )
            prior_efficacy = efficacy * efficacy.waning_factor
            #print(f"  Updated Prior Efficacy: {prior_efficacy}")

        vaccine_trajectory = VaccineTrajectory(
            doses=doses, name=self.name, infection_ids=self.infection_ids
        )
        #print("\n=== Final Vaccine Trajectory ===\n")
        '''print("\n=== SUMMARY OF DOSES ===")

        for dose in vaccine_trajectory.doses:
            print(f"  Dose {dose.number}:")
            print(f"    Date Administered: {dose.date_administered.strftime('%Y-%m-%d')}")
            print(f"    Days to Effective: {dose.days_administered_to_effective}")
            print(f"    Days Effective to Waning: {dose.days_effective_to_waning}")
            print(f"    Days Waning: {dose.days_waning}")
            print(f"    Prior Efficacy: {dose.prior_efficacy}")
            print(f"    Efficacy: {dose.efficacy}")'''
        return vaccine_trajectory


class Vaccines:
    """Vaccines."""

    def __init__(self, vaccines: List[Vaccine]):
        """__init__.

        Parameters
        ----------
        vaccines : List[Vaccine]
            vaccines
        """
        self.vaccines = vaccines
        self.vaccines_dict = {vaccine.name: vaccine for vaccine in vaccines}

    def get_by_name(self, vaccine_name: str):
        """get_by_name.

        Parameters
        ----------
        vaccine_name : str
            vaccine_name
        """
        if vaccine_name not in self.vaccines_dict:
            raise ValueError(f"{vaccine_name} does not exist")
        return self.vaccines_dict[vaccine_name]

    @classmethod
    def from_config_dict(cls, config: dict):
        """
        Create Vaccines from a configuration dictionary.

        Parameters
        ----------
        config : dict
            Dictionary containing vaccine configurations.

        Returns
        -------
        Vaccines
            An instance of Vaccines.

        Notes
        -----
        Returns an empty Vaccines instance if the config is None or empty.
        """
        if not config:  # Handle None or empty dictionary
            print("No vaccine configurations found. Returning an empty Vaccines instance.")
            return cls([])  # Assuming cls([]) creates an empty Vaccines instance

        # Proceed with normal initialization
        vaccines = []
        for vaccine_name, vaccine_data in config.items():
            if vaccine_data:  # Skip empty configurations
                vaccines.append(Vaccine.from_dict(name=vaccine_name, data=vaccine_data))
        return cls(vaccines=vaccines)

    @classmethod
    def from_config(cls, disease_config: DiseaseConfig ):
        """from_config.

        Parameters
        ----------
        config_file : Path
            config_file
        """
        return cls.from_config_dict(config = disease_config.vaccination_manager.get_vaccines())
        """
        print(f"\n=== Loading Vaccine Configuration from File: {config_file} ===")
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        print("Configuration loaded successfully:")
        print(config)
        return cls.from_config_dict(config=config)"""

    def __iter__(
        self,
    ):
        """__iter__."""
        return iter(self.vaccines)

    def get_max_effective_date(
        self,
    ):
        """get_max_effective_date."""
        return max([sum(vaccine.days_to_effective) for vaccine in self.vaccines])
