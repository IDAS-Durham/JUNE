import numpy as np
import pandas as pd

from typing import TYPE_CHECKING

from june.epidemiology.infection.disease_config import DiseaseConfig

if TYPE_CHECKING:
    from june.demography.person import Person

_sex_short_to_long = {"m": "male", "f": "female"}


def _parse_interval(interval):
    age1, age2 = interval.split(",")
    age1 = int(age1.split("[")[-1])
    age2 = int(age2.split("]")[0])
    return pd.Interval(left=age1, right=age2, closed="both")


class HealthIndexGenerator:
    def __init__(
        self,
        disease_config: DiseaseConfig,
        rates_df: pd.DataFrame,
        care_home_min_age: int = 50,
        max_age=99,
        m_exp_baseline=79.4,
        f_exp_baseline=83.1,
        m_exp=79.4,
        f_exp=83.1,
        cutoff_age=16,
    ):
        """
        A Generator to determine the final outcome of an infection.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        rates_df : pd.DataFrame
            A dataframe containing all the different outcome rates.
        care_home_min_age : int
            The age from which a care home resident follows the health index for care homes.
        max_age : int
            Maximum age considered in the health index.
        m_exp_baseline : float
            Baseline male life expectancy.
        f_exp_baseline : float
            Baseline female life expectancy.
        m_exp : float
            Adjusted male life expectancy.
        f_exp : float
            Adjusted female life expectancy.
        cutoff_age : int
            Age at which physiological scaling starts.
        """
        self.care_home_min_age = care_home_min_age
        self.disease_name = disease_config.disease_name
        self.rates_df = rates_df
        self.age_bins = self.rates_df.index
        self.probabilities = self._get_probabilities(disease_config=disease_config, max_age=max_age)
        self.max_mild_symptom_tag = disease_config.symptom_manager.max_mild_symptom_tag      
        self.m_exp_baseline = m_exp_baseline
        self.f_exp_baseline = f_exp_baseline
        self.m_exp = m_exp
        self.f_exp = f_exp
        self.cutoff_age = cutoff_age
        self.use_physiological_age = not (
            self.m_exp_baseline == self.m_exp and self.f_exp_baseline == self.f_exp
        )

        

    @classmethod
    def from_disease_config(
        cls,
        disease_config: DiseaseConfig,
        care_home_min_age=50,
        m_exp_baseline=79.4,
        f_exp_baseline=83.1,
        m_exp=79.4,
        f_exp=83.1,
        cutoff_age=16,
    ):
        """
        Create a HealthIndexGenerator from file.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Preloaded DiseaseConfig object for the disease.
        rates_file : str, optional
            Path to the rates file. Defaults to `disease_config.get_rates_file()`.
        care_home_min_age : int
            Minimum age for care home residents.
        m_exp_baseline : float
            Baseline male life expectancy.
        f_exp_baseline : float
            Baseline female life expectancy.
        m_exp : float
            Adjusted male life expectancy.
        f_exp : float
            Adjusted female life expectancy.
        cutoff_age : int
            Age at which physiological scaling starts.

        Returns
        -------
        HealthIndexGenerator
            A configured HealthIndexGenerator instance.
        """
        rates_file = disease_config.rates_manager.get_rates_file()
        ifrs = pd.read_csv(rates_file, index_col=0)
        ifrs = ifrs.rename(_parse_interval)

        return cls(
            disease_config=disease_config,
            rates_df=ifrs,
            care_home_min_age=care_home_min_age,
            m_exp_baseline=m_exp_baseline,
            f_exp_baseline=f_exp_baseline,
            m_exp=m_exp,
            f_exp=f_exp,
            cutoff_age=cutoff_age,
        )

    def physiological_age(self, person_age, sex):
        if sex == "f":
            exp_baseline_age = self.f_exp_baseline
            exp_age = self.f_exp
        elif sex == "m":
            exp_baseline_age = self.m_exp_baseline
            exp_age = self.m_exp

        if person_age > self.cutoff_age:
            if exp_age == self.cutoff_age:
                return 99
            m = (exp_baseline_age - self.cutoff_age) / (exp_age - self.cutoff_age)
            c = self.cutoff_age * (1 - m)
            scaled_age = person_age * m + c
        else:
            scaled_age = person_age

        if scaled_age > 99.0:
            scaled_age = 99.0
        final_age = int(round(scaled_age))

        return final_age

    def __call__(self, person: "Person", infection_id: int):
        """
        Computes the probability of having all 8 posible outcomes for all ages between 0 and 100,
             self.max_mild_symptom_tag = [
                tag.value for tag in SymptomTag if tag.name == "severe"
            ][0]       for male and female
        Given the person and the id of the infection responsible for the symptoms
        """
        if (
            person.residence is not None
            and person.residence.group.spec == "care_home"
            and person.age >= self.care_home_min_age
        ):
            population = "ch"
        else:
            population = "gp"
        if self.use_physiological_age:
            physiological_age = self.physiological_age(int(person.age), person.sex)
        else:
            physiological_age = int(person.age)
        probabilities = self.probabilities[population][person.sex][physiological_age]
        if infection_id is not None:
            effective_multiplier = person.immunity.get_effective_multiplier(
                infection_id
            )
            if effective_multiplier != 1.0:
                probabilities = self.apply_effective_multiplier(
                    probabilities, effective_multiplier
                )
        
        cum_probabilities = np.cumsum(probabilities)
        return cum_probabilities

    def apply_effective_multiplier(self, probabilities, effective_multiplier):
        modified_probabilities = np.zeros_like(probabilities)
        probability_mild = probabilities[: self.max_mild_symptom_tag].sum()
        probability_severe = probabilities[self.max_mild_symptom_tag :].sum() + (
            1 - probabilities.sum()
        )
        modified_probability_severe = probability_severe * effective_multiplier
        modified_probability_mild = 1.0 - modified_probability_severe
        modified_probabilities[: self.max_mild_symptom_tag] = (
            probabilities[: self.max_mild_symptom_tag]
            * modified_probability_mild
            / probability_mild
        )
        modified_probabilities[self.max_mild_symptom_tag :] = (
            probabilities[self.max_mild_symptom_tag :]
            * modified_probability_severe
            / probability_severe
        )
        return modified_probabilities
    
    def _set_probability_per_age_bin(self, p, age_bin, sex, population, disease_config):
        """
        Populate probabilities for a specific age bin, sex, and population.

        Parameters
        ----------
        p : dict
            Dictionary to store probabilities for each population, sex, and age.
        age_bin : pd.Interval
            Age range (e.g., Interval(0, 9)) for which probabilities are calculated.
        sex : str
            Sex of the individuals ('m' or 'f').
        population : str
            Population type ('ch' for care home, 'gp' for general population).
        disease_config : DiseaseConfig
            Preloaded DiseaseConfig object with configuration details.
        """        
        _sex = _sex_short_to_long[sex]


        # Initialize rates dictionary
        rates = {}

        # Fetch rates dynamically for each parameter in the disease configuration
        for outcome in disease_config.rates_manager.infection_outcome_rates:
            parameter = outcome["parameter"]
            precomputed_rates = disease_config.rates_manager.get_precomputed_rates(
                rates_df=self.rates_df,
                population=population,
                sex=_sex,
                parameter=parameter,
            )

            rates[parameter] = precomputed_rates[age_bin]

        # Initialize probabilities
        n_outcomes = max(disease_config.symptom_manager.symptom_tags.values()) + 1
        probabilities = [0] * n_outcomes

        # Map rates to probabilities using the rate-to-tag mapping
        for rate_name, rate_value in rates.items():
            if rate_name in disease_config.rates_manager.rate_to_tag_mapping:
                symptom_tag_name = disease_config.rates_manager.map_rate_to_tag(rate_name)
                tag_index = disease_config.symptom_manager.get_tag_value(symptom_tag_name)
                probabilities[tag_index] = rate_value

        # Check and process unrated tags if they exist
        if disease_config.rates_manager.unrated_tags:
            for unrated_tag in disease_config.rates_manager.unrated_tags:
                tag_name = unrated_tag["name"]
                rate_dependencies = unrated_tag["rate_calc_dependency"]

                # Retrieve the index for the unrated tag
                tag_index = disease_config.symptom_manager.get_tag_value(tag_name)
                if tag_index is None:
                    raise KeyError(f"Tag '{tag_name}' not found in symptom tags.")
                
                dependent_rate_sum = sum(
                    probabilities[disease_config.symptom_manager.get_tag_value(dep)]
                    for dep in rate_dependencies
                    if disease_config.symptom_manager.get_tag_value(dep) is not None
                )
                calculated_rate = max(0, 1 - dependent_rate_sum)
                probabilities[tag_index] = calculated_rate

        # Ensure stages below the default lowest stage are zero
        default_lowest_stage_index = disease_config.symptom_manager.default_lowest_stage_index
        for i in range(default_lowest_stage_index):
            probabilities[i] = 0

        # Get fatality stage indices
        fatality_stages = disease_config.symptom_manager._resolve_tags("fatality_stage")

        # Separate fatality and non-fatality probabilities
        fatality_probabilities = sum(probabilities[i] for i in fatality_stages)

        non_fatality_probabilities = [
            probabilities[i] if i not in fatality_stages else 0
            for i in range(len(probabilities))
        ]

        # Renormalize non-fatality probabilities
        total_non_fatality = sum(non_fatality_probabilities)

        if total_non_fatality > 0:
            renormalized_non_fatality = [
                val / total_non_fatality * (1 - fatality_probabilities)
                if val > 0 else 0
                for val in non_fatality_probabilities
            ]
        else:
            renormalized_non_fatality = non_fatality_probabilities

        # Combine fatality and renormalized non-fatality probabilities
        final_probabilities = [
            renormalized_non_fatality[i] if i not in fatality_stages else probabilities[i]
            for i in range(len(probabilities))
        ]

        # Assign final probabilities to each age within the age bin
        for age in range(age_bin.left, age_bin.right + 1):
            p[population][sex][age] = final_probabilities
        """
        # Normalize probabilities and assign to age range
        for age in range(age_bin.left, age_bin.right + 1):
            total_rate = sum(probabilities)
            print(f"[DEBUG] Total rate before normalization for age {age}: {total_rate}")
            if total_rate > 0:
                normalized_probabilities = [val / total_rate for val in probabilities]
                p[population][sex][age] = normalized_probabilities
            else:
                p[population][sex][age] = probabilities
            print(f"[DEBUG] Final probabilities for age {age}: {p[population][sex][age]}")"""


        
        
    '''
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
            0, 1 - (hospital_rate + home_dead_rate + asymptomatic_rate + mild_rate)
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
            to_keep_sum = p[population][sex][age][5:].sum()
            to_adjust_sum = p[population][sex][age][:5].sum()
            target_adjust_sum = max(1 - to_keep_sum, 0)
            p[population][sex][age][:5] *= target_adjust_sum / to_adjust_sum
    '''

    def _get_probabilities(self, disease_config: DiseaseConfig, max_age=99):
        """
        Calculate probabilities for each age group and sex dynamically based on the DiseaseConfig.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        max_age : int
            The maximum age to consider for probabilities.

        Returns
        -------
        dict
            A nested dictionary with probabilities for each population, sex, and age.
        """        
        # Extract number of outcomes from symptom tags
        n_outcomes = max(disease_config.symptom_manager.symptom_tags.values()) + 1

        # Initialize probabilities dictionary
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

        # Iterate through populations, sexes, and age bins
        for population in ("ch", "gp"):
            for sex in ["m", "f"]:
                for age_bin in self.age_bins:
                    self._set_probability_per_age_bin(
                        p=probabilities,
                        age_bin=age_bin,
                        sex=sex,
                        population=population,
                        disease_config=disease_config,
                    )
        
        return probabilities