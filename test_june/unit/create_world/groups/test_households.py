import pandas as pd
import pytest

from june.inputs import Inputs


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
            adults = [person for person in household.people if person.age >= 18]
            children = [person for person in household.people if person.age < 18]
            if len(adults) == 0 and len(children) > 0:
                assert False


def test_no_homeless(world_ne):
    """
    Check that no one belonging to an are is left without a house
    """
    total_in_households = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].households)):
            total_in_households += len(world_ne.areas.members[i].households[j].people)

    assert total_in_households == len(world_ne.people.members)


def test_enough_houses(world_ne, inputs):
    """
    Check that we don't have areas with no children in allowed household compositions, but children living
    in that output area. Same for old people.
    """

    OLD_THRESHOLD = 12

    areas_with = (
            inputs["age_freq"][inputs["age_freq"].columns[OLD_THRESHOLD:]].sum(axis=1) > 0
    )
    old_config = [
        c
        for c in inputs["household_composition_freq"].columns
        if int(c.split(" ")[-1]) > 0
    ]
    areas_no_house = (
                         inputs["household_composition_freq"][["0 0 0 3", "0 0 0 2", "0 0 0 1"]]
                     ).sum(axis=1) == 0.0

    assert (
            len(inputs["household_composition_freq"].loc[(areas_no_house) & (areas_with)]) == 0
    )

    CHILDREN_THRESHOLD = 6
    areas_with = (
            inputs["age_freq"][inputs["age_freq"].columns[:CHILDREN_THRESHOLD]].sum(axis=1) > 0
    )
    children_config = [
        c for c in inputs["household_composition_freq"].columns if int(c.split(" ")[0]) > 0
    ]
    areas_no_house = (inputs["household_composition_freq"][children_config]).sum(
        axis=1
    ) == 0.0

    # assert len(input_dict['household_composition_freq'][(areas_no_house) & (areas_with)]) == 0

    areas_with = (
            inputs["age_freq"][inputs["age_freq"].columns[CHILDREN_THRESHOLD:OLD_THRESHOLD]].sum(
                axis=1
            )
            > 0
    )
    adult_config = [
        c for c in inputs["household_composition_freq"].columns if int(c.split(" ")[2]) > 0
    ]
    areas_no_house = (inputs["household_composition_freq"][adult_config]).sum(
        axis=1
    ) == 0.0

    assert (
            len(inputs["household_composition_freq"].loc[(areas_no_house) & (areas_with)]) == 0
    )


if __name__ == "__main__":
    test_enough_houses()
