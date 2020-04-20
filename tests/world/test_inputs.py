import pandas as pd
import numpy as np
from covid.inputs import Inputs
import numpy


def test_frequencies_sum():
    '''
    Test frequencies of each class sum up to 1 in all output areas
    '''

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
    '''
    All frequencies must be positive
    '''

    inputs = Inputs()

    assert np.sum(inputs.age_freq.values < 0.0) == 0
    assert np.sum(inputs.sex_freq.values < 0.0) == 0
    assert np.sum(inputs.household_composition_freq.values < 0.0) == 0



