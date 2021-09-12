import numpy as np
import pandas as pd
from itertools import chain

def parse_age_probabilities(age_dict: dict, fill_value=0):
    """
    Parses the age probability dictionaries into an array.
    """
    if age_dict is None:
        return [0], [0]
    bins = []
    probabilities = []
    for age_range in age_dict:
        age_range_split = age_range.split("-")
        if len(age_range_split) == 1:
            raise NotImplementedError("Please give age ranges as intervals")
        else:
            bins.append(int(age_range_split[0]))
            bins.append(int(age_range_split[1]))
        probabilities.append(age_dict[age_range])
    sorting_idx = np.argsort(bins[::2])
    bins = list(chain.from_iterable(
        [bins[2 * idx], bins[2 * idx + 1]] for idx in sorting_idx
    ))
    probabilities = np.array(probabilities)[sorting_idx]
    probabilities_binned = []
    for prob in probabilities:
        probabilities_binned.append(fill_value)
        probabilities_binned.append(prob)
    probabilities_binned.append(fill_value)
    probabilities_per_age = []
    for age in range(100):
        idx = np.searchsorted(bins, age + 1)  # we do +1 to include the lower boundary
        probabilities_per_age.append(probabilities_binned[idx])
    return probabilities_per_age


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

def parse_prevalence_comorbidities_in_reference_population(
    comorbidity_prevalence_reference_population
):
    parsed_comorbidity_prevalence = {}
    for comorbidity, values in comorbidity_prevalence_reference_population.items():
        parsed_comorbidity_prevalence[comorbidity] = {
            "f": parse_age_probabilities(values["f"]),
            "m": parse_age_probabilities(values["m"]),
        }
    return parsed_comorbidity_prevalence


