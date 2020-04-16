import pandas as pd
import numpy as np
from covid.inputs import Inputs
import numpy


def test_frequencies_sum():

    inputs = Inputs()
    np.testing.assert_allclose(
        inputs.age_freq.sum(axis=1).values, np.ones(len(inputs.age_freq))
    )
    np.testing.assert_allclose(
        inputs.sex_freq.sum(axis=1).values, np.ones(len(inputs.sex_freq))
    )
    np.testing.assert_allclose(
        inputs.household_composition_freq.sum(axis=1).values,
        np.ones(len(inputs.household_composition_freq)),
    )


def test_positive():

    inputs = Inputs()

    assert np.sum(inputs.age_freq.values < 0.0) == 0
    assert np.sum(inputs.sex_freq.values < 0.0) == 0
    assert np.sum(inputs.household_composition_freq.values < 0.0) == 0


def test_enough_houses():

    inputs = Inputs()

    OLD_THRESHOLD = 12

    areas_with = (
        inputs.age_freq[inputs.age_freq.columns[OLD_THRESHOLD:]].sum(
            axis=1
        )
        > 0
    )
    old_config = [
        c
        for c in inputs.household_composition_freq.columns
        if int(c.split(" ")[-1]) > 0
    ]
    areas_no_house = (
        inputs.household_composition_freq[["0 0 0 3", "0 0 0 2", "0 0 0 1"]]
    ).sum(axis=1) == 0.0

    assert (
        len(
            inputs.household_composition_freq.loc[
                (areas_no_house) & (areas_with)
            ]
        )
        == 0
    )

    CHILDREN_THRESHOLD = 6
    areas_with = (
        inputs.age_freq[inputs.age_freq.columns[:CHILDREN_THRESHOLD]].sum(
            axis=1
        )
        > 0
    )
    children_config = [
        c
        for c in inputs.household_composition_freq.columns
        if int(c.split(" ")[0]) > 0
    ]
    areas_no_house = (inputs.household_composition_freq[children_config]).sum(
        axis=1
    ) == 0.0

    # assert len(input_dict['household_composition_freq'][(areas_no_house) & (areas_with)]) == 0

    areas_with = (
        inputs.age_freq[
            inputs.age_freq.columns[CHILDREN_THRESHOLD:OLD_THRESHOLD]
        ].sum(axis=1)
        > 0
    )
    adult_config = [
        c
        for c in inputs.household_composition_freq.columns
        if int(c.split(" ")[2]) > 0
    ]
    areas_no_house = (inputs.household_composition_freq[adult_config]).sum(
        axis=1
    ) == 0.0

    assert (
        len(
            inputs.household_composition_freq.loc[
                (areas_no_house) & (areas_with)
            ]
        )
        == 0
    )


if __name__ == "__main__":
    test_enough_houses()
