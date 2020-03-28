import pandas as pd
import numpy as np
from covid.inputs import create_input_df
import numpy


def test_populate_postcode():
    df = create_input_df()
    # Test frequencies sum up to one 
    np.testing.assert_equal((df["males"] + df["females"]).values,
            np.ones(len(df)))
 



