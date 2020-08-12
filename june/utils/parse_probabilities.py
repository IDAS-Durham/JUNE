import numpy as np
from itertools import chain

def parse_age_probabilities(age_dict: dict):
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
        probabilities_binned.append(0.0)
        probabilities_binned.append(prob)
    probabilities_binned.append(0.0)
    probabilities_per_age = []
    for age in range(100):
        idx = np.searchsorted(bins, age + 1)  # we do +1 to include the lower boundary
        probabilities_per_age.append(probabilities_binned[idx])
    return probabilities_per_age



