import yaml
from pathlib import Path
from typing import List, Dict, Tuple

from june import paths
from june.demography.person import Person
from june.epidemiology.infection import infection as infection_module
from june.utils.parse_probabilities import parse_age_probabilities

default_config_filename = paths.configs_path / "defaults/policy/vaccines.yaml"


class Vaccine:
    def __init__(
        self,
        name: str,
        n_doses: int,
        days_to_next_dose: List[int],
        days_to_effective: List[int],
        sterilisation_efficacies,
        symptomatic_efficacies,
    ):
        """
        Class defining a vaccine type and its effectiveness

        Parameters
        ----------
        name:
           vaccine name
        days_to_next_dose:
            number of days to wait for next dose
        days_to_effective:
            number of days it takes for current dose to be fully effective
        sterilisation_efficacy
            final full efficacy against infection, by variant and age
        symptomatic_efficacy
            final full efficacy against symptoms, by variant and age
        """

        self.name = name
        self.n_doses = n_doses
        self.days_to_next_dose = days_to_next_dose
        self.days_to_effective = days_to_effective
        self.sterilisation_efficacies = self._parse_efficacies(sterilisation_efficacies)
        self.symptomatic_efficacies = self._parse_efficacies(symptomatic_efficacies)
        print('Sterrr')
        person = Person(age=50)
        print(self.get_efficacy_for_dose_person(person, dose=0))
        print(self.get_efficacy_for_dose_person(person, dose=1))

    @classmethod
    def from_config(
        cls,
        vaccine_type: str,
        n_doses: int,
        config_file: Path = default_config_filename,
    ):
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        config = config[vaccine_type]
        return cls(
            name=vaccine_type,
            n_doses=n_doses,
            days_to_next_dose=config["days_to_next_dose"],
            days_to_effective=config["days_to_effective"],
            sterilisation_efficacies=config["sterilisation_efficacies"],
            symptomatic_efficacies=config["symptomatic_efficacies"],
        )

    def _parse_efficacies(self, efficacies):
        ret = []
        for dd in efficacies:
            dd_id = {}
            for key in dd:
                infection_id = getattr(infection_module, key).infection_id()
                dd_id[infection_id] = parse_age_probabilities(dd[key])
            ret.append(dd_id)
        return ret

    def get_efficacy(
        self, person: Person, infection_id: int, dose: int
    ) -> Tuple[float, float]:
        """
        Get sterilisation and symptomatic efficacy of a given dose
        for a person and variant

        Parameters
        ----------
        person:
            person to get efficacy for
        infection_id:
            id of the infection
        dose:
            dose number
        """
        return (
            self.sterilisation_efficacies[dose][infection_id][person.age],
            self.symptomatic_efficacies[dose][infection_id][person.age],
        )

    def get_efficacy_for_dose_person(
        self, person: Person, dose: int
    ) -> Tuple[float, float]:
        """
        Get sterilisation and symptomatic efficacy of a given dose
        for a person and variant

        Parameters
        ----------
        person:
            person to get efficacy for
        dose:
            dose number
        """

        return (
            self.select_dose_age(
                self.sterilisation_efficacies, dose=dose, age=person.age
            ),
            self.select_dose_age(
                self.symptomatic_efficacies, dose=dose, age=person.age
            ),
        )

    def select_dose_age(self, efficacy, dose, age):
        return {k: v[age] for k, v in efficacy[dose].items()}
