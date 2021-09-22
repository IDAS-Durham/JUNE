from typing import Optional
import numpy as np
from random import random
from june.utils import (
    parse_age_probabilities,
    parse_prevalence_comorbidities_in_reference_population,
    read_comorbidity_csv,
    convert_comorbidities_prevalence_to_dict,
)

from . import Covid19, B117, B16172

default_susceptibility_dict = {
    Covid19.infection_id(): {"0-13": 0.5, "13-100": 1.0},
    B117.infection_id(): {"0-13": 0.5, "13-100": 1.0},
    B16172.infection_id(): {"0-13": 0.5, "13-100": 1.0},
}
default_multiplier_dict = {
    Covid19.infection_id(): 1.0,
    B117.infection_id(): 1.5,
    B16172.infection_id(): 1.5,
}


class ImmunitySetter:
    def __init__(
        self,
        susceptibility_dict: dict = default_susceptibility_dict,
        multiplier_dict: dict = default_multiplier_dict,
        vaccination_dict: dict = None,
        previous_infections_dict=None,
        multiplier_by_comorbidity: Optional[dict] = None,
        comorbidity_prevalence_reference_population: Optional[dict] = None,
        susceptibility_mode="average",
        record: "Record" = None,
    ):
        """
        Sets immnuity parameters to different viruses.

        Parameters
        ----------
        susceptibility_dict:
           A dictionary mapping infection_id -> susceptibility by age.
           Example:
            susceptibility_dict = {"123" : {"0-50" : 0.5, "50-100" : 0.2}}
        multiplier_dict:
           A dictionary mapping infection_id -> symptoms reduction by age.
           Example:
            multiplier_dict = {"123" : {"0-50" : 0.5, "50-100" : 0.2}}
        vaccination_dict:
            A dictionary specifying the starting vaccination status of the population.
            Example:
                vaccination_dict = {
                    "pfizer": {
                        "percentage_vaccinated": {"0-50": 0.7, "50-100": 1.0},
                        "infections": {
                            Covid19.infection_id(): {
                                "sterilisation_efficacy": {"0-100": 0.5},
                                "symptomatic_efficacy": {"0-100": 0.5},
                            },
                        },
                    },
                    "sputnik": {
                        "percentage_vaccinated": {"0-30": 0.3, "30-100": 0.0},
                        "infections": {
                            B117.infection_id(): {
                                "sterilisation_efficacy": {"0-100": 0.8},
                                "symptomatic_efficacy": {"0-100": 0.8},
                            },
                        },
                    },
                }
            previous_infections_dict:
                A dictionary specifying the current seroprevalence per region and age.
                Example:
                    previous_infections_dict = {
                        "infections": {
                            Covid19.infection_id(): {
                                "sterilisation_efficacy": 0.5,
                                "symptomatic_efficacy": 0.6,
                            },
                            B117.infection_id(): {
                                "sterilisation_efficacy": 0.2,
                                "symptomatic_efficacy": 0.3,
                            },
                        },
                        "ratios": {
                            "London": {"0-50": 0.5, "50-100": 0.2},
                            "North East": {"0-70": 0.3, "70-100": 0.8},
                        },
                    }
        """
        self.susceptibility_dict = self._read_susceptibility_dict(susceptibility_dict)
        if multiplier_dict is None:
            self.multiplier_dict = {}
        else:
            self.multiplier_dict = multiplier_dict
        self.vaccination_dict = self._read_vaccination_dict(vaccination_dict)
        self.previous_infections_dict = self._read_previous_infections_dict(
            previous_infections_dict
        )
        self.multiplier_by_comorbidity = multiplier_by_comorbidity
        if comorbidity_prevalence_reference_population is not None:
            self.comorbidity_prevalence_reference_population = (
                parse_prevalence_comorbidities_in_reference_population(
                    comorbidity_prevalence_reference_population
                )
            )
        else:
            self.comorbidity_prevalence_reference_population = None
        self.susceptibility_mode = susceptibility_mode
        self.record = record

    @classmethod
    def from_file_with_comorbidities(
        cls,
        susceptibility_dict: dict = default_susceptibility_dict,
        multiplier_dict: dict = default_multiplier_dict,
        vaccination_dict: dict = None,
        previous_infections_dict: dict = None,
        comorbidity_multipliers_path: Optional[str] = None,
        male_comorbidity_reference_prevalence_path: Optional[str] = None,
        female_comorbidity_reference_prevalence_path: Optional[str] = None,
        susceptibility_mode="average",
        record:"Record"=None,
    ) -> "ImmunitySetter":
        if comorbidity_multipliers_path is not None:
            with open(comorbidity_multipliers_path) as f:
                comorbidity_multipliers = yaml.load(f, Loader=yaml.FullLoader)
            female_prevalence = read_comorbidity_csv(
                female_comorbidity_reference_prevalence_path
            )
            male_prevalence = read_comorbidity_csv(
                male_comorbidity_reference_prevalence_path
            )
            comorbidity_prevalence_reference_population = (
                convert_comorbidities_prevalence_to_dict(
                    female_prevalence, male_prevalence
                )
            )
        else:
            comorbidity_multipliers = None
            comorbidity_prevalence_reference_population = None
        return ImmunitySetter(
            susceptibility_dict=susceptibility_dict,
            multiplier_dict=multiplier_dict,
            vaccination_dict=vaccination_dict,
            previous_infections_dict=previous_infections_dict,
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
            susceptibility_mode=susceptibility_mode,
            record=record,
        )

    def set_immunity(self, population):
        if self.multiplier_dict:
            self.set_multipliers(population)
        if self.susceptibility_dict:
            self.set_susceptibilities(population)
        if self.previous_infections_dict:
            self.set_previous_infections(population)
        if self.vaccination_dict:
            self.set_vaccinations(population)

    def get_multiplier_from_reference_prevalence(self, age, sex):
        """
        Compute mean comorbidity multiplier given the prevalence of the different comorbidities
        in the reference population (for example the UK). It will be used to remove effect of
        comorbidities in the reference population
        Parameters
        ----------
        age:
            age group to compute average multiplier
        sex:
            sex group to compute average multiplier
        Returns
        -------
            weighted_multiplier:
                weighted mean of the multipliers given prevalence
        """
        weighted_multiplier = 0.0
        for comorbidity in self.comorbidity_prevalence_reference_population.keys():
            weighted_multiplier += (
                self.multiplier_by_comorbidity[comorbidity]
                * self.comorbidity_prevalence_reference_population[comorbidity][sex][
                    age
                ]
            )
        return weighted_multiplier

    def get_weighted_multipliers_by_age_sex(
        self,
    ):
        reference_multipliers = {"m": [], "f": []}
        for sex in ("m", "f"):
            for age in range(100):
                reference_multipliers[sex].append(
                    self.get_multiplier_from_reference_prevalence(age=age, sex=sex)
                )
        return reference_multipliers

    def set_multipliers(self, population):
        if (
            self.multiplier_by_comorbidity is not None
            and self.comorbidity_prevalence_reference_population is not None
        ):
            set_comorbidity_multipliers = True
            reference_weighted_multipliers = self.get_weighted_multipliers_by_age_sex()
        else:
            set_comorbidity_multipliers = False
        for person in population:
            for inf_id in self.multiplier_dict:
                person.immunity.effective_multiplier_dict[
                    inf_id
                ] = self.multiplier_dict[inf_id]
                if set_comorbidity_multipliers:
                    multiplier = self.multiplier_by_comorbidity.get(
                        person.comorbidity, 1.0
                    )
                    reference_multiplier = reference_weighted_multipliers[person.sex][
                        person.age
                    ]
                    person.immunity.effective_multiplier_dict[inf_id] += (
                        multiplier / reference_multiplier
                    ) - 1.0

    def _read_susceptibility_dict(self, susceptibility_dict):
        if susceptibility_dict is None:
            return {}
        ret = {}
        for inf_id in susceptibility_dict:
            ret[inf_id] = parse_age_probabilities(
                susceptibility_dict[inf_id], fill_value=1.0
            )
        return ret

    def _read_vaccination_dict(self, vaccination_dict):
        if vaccination_dict is None:
            return {}
        ret = {}
        for vaccine, vdata in vaccination_dict.items():
            ret[vaccine] = {}
            ret[vaccine]["percentage_vaccinated"] = parse_age_probabilities(
                vdata["percentage_vaccinated"]
            )
            ret[vaccine]["infections"] = {}
            for inf_id in vdata["infections"]:
                ret[vaccine]["infections"][inf_id] = {}
                for key in vdata["infections"][inf_id]:
                    ret[vaccine]["infections"][inf_id][key] = parse_age_probabilities(
                        vdata["infections"][inf_id][key], fill_value=0.0
                    )
        return ret

    def _read_previous_infections_dict(self, previous_infections_dict):
        if previous_infections_dict is None:
            return {}
        ret = {}
        ret["infections"] = previous_infections_dict["infections"]
        ret["ratios"] = {}
        for region, region_ratios in previous_infections_dict["ratios"].items():
            ret["ratios"][region] = parse_age_probabilities(region_ratios)
        return ret

    def set_susceptibilities(self, population):
        if self.susceptibility_mode == "average":
            self._set_susceptibilities_avg(population)
        elif self.susceptibility_mode == "individual":
            self._set_susceptibilities_individual(population)
        else:
            raise NotImplementedError()

    def _set_susceptibilities_avg(self, population):
        for person in population:
            for inf_id in self.susceptibility_dict:
                if person.age >= len(self.susceptibility_dict[inf_id]):
                    continue
                person.immunity.susceptibility_dict[inf_id] = self.susceptibility_dict[
                    inf_id
                ][person.age]

    def _set_susceptibilities_individual(self, population):
        for person in population:
            for inf_id in self.susceptibility_dict:
                if person.age >= len(self.susceptibility_dict[inf_id]):
                    continue
                fraction = self.susceptibility_dict[inf_id][person.age]
                if random() > fraction:
                    person.immunity.susceptibility_dict[inf_id] = 0.0

    def set_vaccinations(self, population):
        """
        Sets previous vaccination on the starting population.
        """
        vaccine_type = []
        susccesfully_vaccinated = np.zeros(len(population), dtype=int)
        if not self.vaccination_dict:
            return
        vaccines = list(self.vaccination_dict.keys())
        for i, person in enumerate(population):
            if person.age > 99:
                age = 99
            else:
                age = person.age
            vaccination_rates = np.array(
                [
                    self.vaccination_dict[vaccine]["percentage_vaccinated"][age]
                    for vaccine in vaccines
                ]
            )
            total_vacc_rate = np.sum(vaccination_rates)
            if random() < total_vacc_rate:
                vaccination_rates /= total_vacc_rate
                vaccine = np.random.choice(vaccines, p=vaccination_rates)
                vdata = self.vaccination_dict[vaccine]
                for inf_id, inf_data in vdata["infections"].items():
                    person.immunity.add_multiplier(
                        inf_id, 1.0 - inf_data["symptomatic_efficacy"][age]
                    )
                    person.immunity.susceptibility_dict[inf_id] = (
                        1.0 - inf_data["sterilisation_efficacy"][age]
                    )
                    susccesfully_vaccinated[i] = 1
                person.vaccinated = True
                vaccine_type.append(vaccine)
            else:
                vaccine_type.append("none")
        if self.record is not None:
            self.record.statics["people"].extra_str_data["vaccine_type"] = vaccine_type
            self.record.statics["people"].extra_int_data[
                "susccesfully_vaccinated"
            ] = susccesfully_vaccinated

    def set_previous_infections(self, population):
        """
        Sets previous infections on the starting population.
        """
        previously_infected = np.zeros(len(population), dtype=int)
        for i, person in enumerate(population):
            if person.region.name not in self.previous_infections_dict["ratios"]:
                continue
            ratio = self.previous_infections_dict["ratios"][person.region.name][
                person.age
            ]
            if random() < ratio:
                for inf_id, inf_data in self.previous_infections_dict[
                    "infections"
                ].items():
                    person.immunity.add_multiplier(
                        inf_id, 1.0 - inf_data["symptomatic_efficacy"]
                    )
                    person.immunity.susceptibility_dict[inf_id] = (
                        1.0 - inf_data["sterilisation_efficacy"]
                    )
        if self.record is not None:
            self.record.statics["people"].extra_int_data[
                "previously_infected"
            ] = previously_infected
