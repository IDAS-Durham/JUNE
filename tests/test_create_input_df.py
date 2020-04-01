import pandas as pd
import numpy as np
from covid.inputs import create_input_dict
import numpy


def test_frequencies_sum():
    input_dict = create_input_dict()

    for key, value in input_dict.items():
        if "freq" in key:

            np.testing.assert_allclose(
                input_dict[key].sum(axis=1).values, np.ones(len(input_dict[key])),
            )

def test_positive():

    input_dict = create_input_dict()
    for key, value in input_dict.items():
        if "freq" in key:
             assert any(input_dict[key] < 0.) == False
