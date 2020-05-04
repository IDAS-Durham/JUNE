import pandas as pd
import numpy as np
from covid.inputs import Inputs
from covid.groups import Schools
import numpy


def test__frequencies_sum():
    """
    Test frequencies of each distribution input sum up to 1
    """

    inputs = Inputs()
    # sum up to 1 in all output areas
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
    m_columns = [
        col
        for col in inputs.compsec_by_sex_df.columns.values
        if "m " in col
    ]
    f_columns = [
        col 
        for col in inputs.compsec_by_sex_df.columns.values
        if "f " in col
    ]
    np.testing.assert_allclose(
        inputs.compsec_by_sex_df.loc[:, m_columns].sum(axis=1).values,
        np.ones(len(inputs.compsec_by_sex_df)),
    )

def test__positive():
    """
    All frequencies must be positive
    """

    inputs = Inputs()

    assert np.sum(inputs.age_freq.values < 0.0) == 0
    assert np.sum(inputs.sex_freq.values < 0.0) == 0
    assert np.sum(inputs.household_composition_freq.values < 0.0) == 0
    assert np.sum(inputs.compsec_by_sex_df.values < 0.0) == 0
    assert np.sum(inputs.companysize_df.values < 0.0) == 0

#def test__area_intersections():
#    """
#    Check that the provided input data includes the same areas
#    """
#    inputs = Inputs()
#    school_df = pd.read_csv(
#        self.inputs.school_data_path,
#        index_col=0,
#    )

