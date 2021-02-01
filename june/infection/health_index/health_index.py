import numpy as np
import pandas as pd
import yaml
from typing import Optional, List

from june.infection.symptom_tag import SymptomTag
from june import paths
from june.utils.parse_probabilities import parse_age_probabilities
from . import Data2Rates

_sex_short_to_long = {"m": "male", "f": "female"}
index_to_maximum_symptoms_tag = {
    0: "asymptomatic",
    1: "mild",
    2: "severe",
    3: "hospitalised",
    4: "intensive_care",
    5: "dead_home",
    6: "dead_hospital",
    7: "dead_icu",
}

default_rates_file = paths.data_path / "input/health_index/infection_outcome_rates.csv"


def _parse_interval(interval):
    age1, age2 = interval.split(",")
    age1 = int(age1.split("[")[-1])
    age2 = int(age2.split("]")[0])
    return pd.Interval(left=age1, right=age2, closed="both")


class HealthIndexGenerator:
    def __init__(
        self,
        rates_df: pd.DataFrame,
        care_home_min_age: int = 50,
        max_age=99,
        use_comorbidities: bool = False,
        comorbidity_multipliers: Optional[dict] = None,
        comorbidity_prevalence_reference_population: Optional[dict] = None,
    ):
        """
        A Generator to determine the final outcome of an infection.

        Parameters
        ----------
        rates_df
            a dataframe containing all the different outcome rates,
            check the default file for a reference
        care_home_min_age
            the age from which a care home resident follows the health index
            for care homes.
        """
        self.care_home_min_age = care_home_min_age
        self.rates_df = rates_df
        self.age_bins = self.rates_df.index
        self.probabilities = self._get_probabilities(max_age)
        self.use_comorbidities = use_comorbidities
        if self.use_comorbidities:
            self.max_mild_symptom_tag = {
                value: key for key, value in index_to_maximum_symptoms_tag.items()
            }["severe"]
            self.comorbidity_multipliers = comorbidity_multipliers
            self.comorbidity_prevalence_reference_population = (
                self._parse_prevalence_comorbidities_in_reference_population(
                    comorbidity_prevalence_reference_population
                )
            )

    @classmethod
    def from_file(
        cls,
        rates_file: str = default_rates_file,
        care_home_min_age=50,
        use_comorbidities=False,
        comorbidity_multipliers=None,
        comorbidity_prevalence_reference_population=None,
    ):
        ifrs = pd.read_csv(rates_file, index_col=0)
        ifrs = ifrs.rename(_parse_interval)
        return cls(
            rates_df=ifrs,
            care_home_min_age=care_home_min_age,
            use_comorbidities=use_comorbidities,
            comorbidity_multipliers=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
        )

    @classmethod
    def from_file_with_comorbidities(
        cls,
        multipliers_path: str,
        male_prevalence_path: str,
        female_prevalence_path: str,
        rates_file: str = default_rates_file,
        care_home_min_age=50,
    ) -> "HealthIndexGenerator":

        with open(multipliers_path) as f:
            comorbidity_multipliers = yaml.load(f, Loader=yaml.FullLoader)
        female_prevalence = read_comorbidity_csv(female_prevalence_path)
        male_prevalence = read_comorbidity_csv(male_prevalence_path)
        comorbidity_prevalence_reference_population = (
            convert_comorbidities_prevalence_to_dict(female_prevalence, male_prevalence)
        )
        return cls.from_file(
            rates_file=rates_file,
            care_home_min_age=care_home_min_age,
            use_comorbidities=True,
            comorbidity_multipliers=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
        )

    def __call__(self, person):
        """
        Computes the probability of having all 8 posible outcomes for all ages between 0 and 100,
             self.max_mild_symptom_tag = [
                tag.value for tag in SymptomTag if tag.name == "severe"
            ][0]       for male and female
        """
        if (
            person.residence is not None
            and person.residence.group.spec == "care_home"
            and person.age >= self.care_home_min_age
        ):
            population = "ch"
        else:
            population = "gp"
        probabilities = self.probabilities[population][person.sex][person.age]
        if self.use_comorbidities and person.comorbidity is not None:
            probabilities = self.adjust_for_comorbidities(
                probabilities=probabilities,
                comorbidity=person.comorbidity,
                age=person.age,
                sex=person.sex,
            )
        return np.cumsum(probabilities)

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
                self.comorbidity_multipliers[comorbidity]
                * self.comorbidity_prevalence_reference_population[comorbidity][sex][
                    age
                ]
            )
        return weighted_multiplier

    def adjust_for_comorbidities(
        self, probabilities: List[float], comorbidity: str, age: int, sex: str
    ):
        """
        Compute adjusted probabilities for a person with given comorbidity, age and sex.
        Parameters
        ----------
        probabilities:
            list with probability values for the 8 different outcomes (has len 7, but 8th value
            can be inferred from 1 - probabilities.sum())
        comorbidity:
            comorbidty type that the person has
        age:
            age group to compute average multiplier
        sex:
            sex group to compute average multiplier
        Returns
        -------
            probabilities adjusted for comorbidity
        """

        multiplier = self.comorbidity_multipliers.get(comorbidity, 1.0)
        reference_weighted_multiplier = self.get_multiplier_from_reference_prevalence(
            age=age, sex=sex
        )
        effective_multiplier = multiplier / reference_weighted_multiplier
        return self.apply_effective_multiplier(
            probabilities=probabilities, effective_multiplier=effective_multiplier
        )

    def apply_effective_multiplier(self, probabilities, effective_multiplier):
        probabilities_with_comorbidity = np.zeros_like(probabilities)
        p_mild = probabilities[: self.max_mild_symptom_tag].sum()
        p_severe = probabilities[self.max_mild_symptom_tag :].sum() + (
            1 - probabilities.sum()
        )
        p_severe_with_comorbidity = p_severe * effective_multiplier
        p_mild_with_comorbidity = 1 - p_severe_with_comorbidity
        probabilities_with_comorbidity[: self.max_mild_symptom_tag] = (
            probabilities[: self.max_mild_symptom_tag]
            * p_mild_with_comorbidity
            / p_mild
        )
        probabilities_with_comorbidity[self.max_mild_symptom_tag :] = (
            probabilities[self.max_mild_symptom_tag :]
            * p_severe_with_comorbidity
            / p_severe
        )
        return probabilities_with_comorbidity

    def _set_probability_per_age_bin(self, p, age_bin, sex, population):
        _sex = _sex_short_to_long[sex]
        asymptomatic_rate = self.rates_df.loc[
            age_bin, f"{population}_asymptomatic_{_sex}"
        ]
        mild_rate = self.rates_df.loc[age_bin, f"{population}_mild_{_sex}"]
        hospital_rate = self.rates_df.loc[age_bin, f"{population}_hospital_{_sex}"]
        icu_rate = self.rates_df.loc[age_bin, f"{population}_icu_{_sex}"]
        home_dead_rate = self.rates_df.loc[age_bin, f"{population}_home_ifr_{_sex}"]
        hospital_dead_rate = self.rates_df.loc[
            age_bin, f"{population}_hospital_ifr_{_sex}"
        ]
        icu_dead_rate = self.rates_df.loc[age_bin, f"{population}_icu_ifr_{_sex}"]
        severe_rate = max(
            0,
            1 - (hospital_rate + home_dead_rate + asymptomatic_rate + mild_rate),
        )
        # fill each age in bin
        for age in range(age_bin.left, age_bin.right + 1):
            p[population][sex][age][0] = asymptomatic_rate  # recovers as asymptomatic
            p[population][sex][age][1] = mild_rate  # recovers as mild
            p[population][sex][age][2] = severe_rate  # recovers as severe
            p[population][sex][age][3] = (
                hospital_rate - hospital_dead_rate
            )  # recovers in the ward
            p[population][sex][age][4] = max(
                icu_rate - icu_dead_rate, 0
            )  # recovers in the icu
            p[population][sex][age][5] = max(home_dead_rate, 0)  # dies at home
            p[population][sex][age][6] = max(
                hospital_dead_rate - icu_dead_rate, 0
            )  # dies in the ward
            p[population][sex][age][7] = icu_dead_rate
            # renormalise all but death rates (since those are the most certain ones)
            total = p[population][sex][age].sum()
            to_keep_sum = p[population][sex][age][5:].sum()
            to_adjust_sum = p[population][sex][age][:5].sum()
            target_adjust_sum = max(1 - to_keep_sum, 0)
            p[population][sex][age][:5] *= target_adjust_sum / to_adjust_sum

    def _get_probabilities(self, max_age=99):
        n_outcomes = 8
        probabilities = {
            "ch": {
                "m": np.zeros((max_age + 1, n_outcomes)),
                "f": np.zeros((max_age + 1, n_outcomes)),
            },
            "gp": {
                "m": np.zeros((max_age + 1, n_outcomes)),
                "f": np.zeros((max_age + 1, n_outcomes)),
            },
        }
        for population in ("ch", "gp"):
            for sex in ["m", "f"]:
                # values are constant at each bin
                for age_bin in self.age_bins:
                    self._set_probability_per_age_bin(
                        p=probabilities,
                        age_bin=age_bin,
                        sex=sex,
                        population=population,
                    )
        return probabilities

    def _parse_prevalence_comorbidities_in_reference_population(
        self, comorbidity_prevalence_reference_population
    ):
        parsed_comorbidity_prevalence = {}
        for comorbidity, values in comorbidity_prevalence_reference_population.items():
            parsed_comorbidity_prevalence[comorbidity] = {
                "f": parse_age_probabilities(values["f"]),
                "m": parse_age_probabilities(values["m"]),
            }
        return parsed_comorbidity_prevalence


def read_comorbidity_csv(filename: str):
    comorbidity_df = pd.read_csv(filename, index_col=0)
    column_names = [f"0-{comorbidity_df.columns[0]}"]
    for i in range(len(comorbidity_df.columns) - 1):
        column_names.append(
            f"{comorbidity_df.columns[i]}-{comorbidity_df.columns[i+1]}"
        )
    comorbidity_df.columns = column_names
    for column in comorbidity_df.columns:
        no_comorbidity = comorbidity_df[column].loc["no_condition"]
        should_have_comorbidity = 1 - no_comorbidity
        has_comorbidity = np.sum(comorbidity_df[column]) - no_comorbidity
        comorbidity_df[column].iloc[:-1] *= should_have_comorbidity / has_comorbidity

    return comorbidity_df.T


def convert_comorbidities_prevalence_to_dict(prevalence_female, prevalence_male):
    prevalence_reference_population = {}
    for comorbidity in prevalence_female.columns:
        prevalence_reference_population[comorbidity] = {
            "f": prevalence_female[comorbidity].to_dict(),
            "m": prevalence_male[comorbidity].to_dict(),
        }
    return prevalence_reference_population
