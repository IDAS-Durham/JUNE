import pandas as pd
import pytest

from covid.inputs import Inputs


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
    for area in world_ne.areas.members:
        for household in area.households:
            adults = [person for grouping in household.groupings for person in grouping  if person.age >= 18]
            children = [person for grouping in household.groupings for person in grouping if person.age < 18]
            if len(adults) == 0 and len(children) > 0:
                assert False


def test_no_homeless(world_ne):
    """
    Check that no one belonging to an are is left without a house
    """
    people_in_households = set()
    for member in world_ne.areas.members:
        for household in member.households:
            for grouping in household.groupings:
                people_in_households.update(grouping._people) 

    assert len(people_in_households) == len(world_ne.people.members)

