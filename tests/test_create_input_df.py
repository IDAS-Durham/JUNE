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
            print(key)
            assert np.sum(input_dict[key].values < 0.) == 0

def test_enough_houses():

    OLD_THRESHOLD = 12

    input_dict = create_input_dict()

    areas_with = input_dict['age_freq'][input_dict['age_freq'].columns[OLD_THRESHOLD:]].sum(axis=1) > 0
    old_config = [c for c in input_dict['household_composition_freq'].columns if int(c.split(' ')[-1])>0 ]
    areas_no_house = (input_dict['household_composition_freq'][['0 0 0 3', '0 0 0 2', '0 0 0 1']]).sum(axis=1) == 0.

    assert len(input_dict['household_composition_freq'][(areas_no_house) & (areas_with)]) == 0

    CHILDREN_THRESHOLD = 6
    areas_with = input_dict['age_freq'][input_dict['age_freq'].columns[:CHILDREN_THRESHOLD]].sum(axis=1) > 0
    children_config = [c for c in input_dict['household_composition_freq'].columns if int(c.split(' ')[0])>0 ]
    areas_no_house = (input_dict['household_composition_freq'][children_config]).sum(axis=1) == 0.

    assert len(input_dict['household_composition_freq'][(areas_no_house) & (areas_with)]) == 0

 
if __name__=='__main__':
    test_enough_houses()
