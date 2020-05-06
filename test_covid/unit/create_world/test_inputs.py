import pandas as pd
import numpy as np
from covid.inputs import Inputs
from covid.groups import Schools
from covid.groups.areas import Areas
import numpy


def test__frequencies_sum():
    """
    Test frequencies of each distribution input sum up to 1
    """

    inputs = Inputs()
    # read from input file
    age_freq_df = Areas.read(
        inputs.age_freq_file,
    )[0]
    sex_freq_df = Areas.read(
        inputs.sex_freq_file,
    )[0]
    household_composition_freq_df = Areas.read(
        inputs.household_composition_freq_file,
    )[0]
    # sum up to 1 in all output areas
    np.testing.assert_allclose(
        age_freq_df.sum(axis=1).values, np.ones(len(age_freq_df))
    )
    np.testing.assert_allclose(
        sex_freq_df.sum(axis=1).values, np.ones(len(sex_freq_df))
    )
    np.testing.assert_allclose(
        household_composition_freq_df.sum(axis=1).values,
        np.ones(len(household_composition_freq_df)),
    )

def test__positive():
    """
    All frequencies must be positive
    """

    inputs = Inputs()
    # read from input file
    age_freq_df = pd.read_csv(
        inputs.age_freq_file,
        index_col=0,
    )
    sex_freq_df = pd.read_csv(
        inputs.sex_freq_file,
        index_col=0,
    )
    household_composition_freq_df = pd.read_csv(
        inputs.household_composition_freq_file,
        index_col=0,
    )
    assert np.sum(age_freq_df.values < 0.0) == 0
    assert np.sum(sex_freq_df.values < 0.0) == 0
    assert np.sum(household_composition_freq_df.values < 0.0) == 0

def test__area_intersections():
    """
    Check that the provided input data includes the same areas
    """
    inputs = Inputs()
    school_df = pd.read_csv(
        inputs.school_data_path,
        index_col=0,
    )
    n_residents_df = pd.read_csv(
        inputs.n_residents_file,
        index_col=0,
    )
    age_freq_df = pd.read_csv(
        inputs.age_freq_file,
        index_col=0,
    )
    sex_freq_df = pd.read_csv(
        inputs.sex_freq_file,
        index_col=0,
    )
    household_composition_freq_df = pd.read_csv(
        inputs.household_composition_freq_file,
        index_col=0,
    )
