import os
import numpy as np
import pandas as pd
import pytest
from covid.inputs import Inputs
from covid.groups import Household, Households


@pytest.fixture(name="inputs")
def get_input_data():
    
    def read(filename: str):
        df = pd.read_csv(filename, index_col="output_area")
        freq = df.div(df.sum(axis=1), axis=0)
        decoder = {i: df.columns[i] for i in range(df.shape[-1])}
        return freq, decoder
    
    inputs = Inputs(zone="test")
    n_residents = pd.read_csv(
        inputs.n_residents_file,
        names=["output_area", "counts"],
        header=0,
        index_col="output_area",
    )
    age_freq, decoder_age = read(inputs.age_freq_file)
    sex_freq, decoder_sex = read(inputs.sex_freq_file)
    (
        household_composition_freq,
        decoder_household_composition,
    ) = read(
        inputs.household_composition_freq_file
    )
    encoder_household_composition = {}
    for i, column in enumerate(household_composition_freq.columns):
        encoder_household_composition[column] = i
    inputs = {
        "n_residents": n_residents,
        "age_freq": age_freq,
        "decoder_age": decoder_age,
        "sex_freq": sex_freq,
        "decoder_sex": decoder_sex,
        "household_composition_freq": household_composition_freq,    
        "decoder_household_composition": decoder_household_composition,
        "encoder_household_composition": encoder_household_composition,
    }
    return inputs


def test_no_lonely_children(world_ne, inputs):
    """
    Check there ar eno children living without adults
    """
    only_children = 0
    for household in world_ne.households.members:
        has_children = False
        has_adults = False
        for person in household.people:
            if person.age < 18:
                has_children = True
            if person.age >= 18:
                has_adults = True
        if has_children and not has_adults:
            only_children += 1

    assert only_children == 0


def test__no_homeless(world_ne):
    """
    Check that no one belonging to an are is left without a house
    """
    total_in_carehomes = 0
    for carehome in world_ne.carehomes.members:
        total_in_carehomes += len(carehome.people)
    total_in_households = total_in_carehomes
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].households)):
            total_in_households += len(world_ne.areas.members[i].households[j].people)

    assert total_in_households == len(world_ne.people.members)

def test__households_adding():
    households1 = Households()
    households1.members = [1,2,3]
    households2 = Households()
    households2.members = [4,5]
    households3 = households1 + households2
    assert households3.members == [1,2,3,4,5]



