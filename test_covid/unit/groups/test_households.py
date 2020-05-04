import numpy as np
import os


def test_no_lonely_children(world_ne):
    """
    Check there ar eno children living without adults
    """

    attribute = "nomis_bin"
    decoder = world_ne.inputs.decoder_age
    only_children = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].households)):
            freq = np.zeros(len(decoder))
            for k in range(len(world_ne.areas.members[i].households[j].people)):
                freq[
                    getattr(world_ne.areas.members[i].households[j].people[k], attribute)
                ] += 1
                # if no adults, but at least one child
                if (np.sum(freq[5:]) == 0.0) & (np.sum(freq[:5]) > 0.0):
                    only_children += 1

    assert only_children == 0


def test_no_homeless(world_ne):
    """
    Check that no one belonging to an are is left without a house
    """
    total_in_households = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].households)):
            total_in_households += len(world_ne.areas.members[i].households[j].people)

    assert total_in_households == len(world_ne.people.members)


def test_enough_houses(world_ne):
    """
    Check that we don't have areas with no children in allowed household compositions, but children living
    in that output area. Same for old people.
    """

    inputs = world_ne.inputs

    OLD_THRESHOLD = 12

    areas_with = (
        inputs.age_freq[inputs.age_freq.columns[OLD_THRESHOLD:]].sum(axis=1) > 0
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
        len(inputs.household_composition_freq.loc[(areas_no_house) & (areas_with)]) == 0
    )

    CHILDREN_THRESHOLD = 6
    areas_with = (
        inputs.age_freq[inputs.age_freq.columns[:CHILDREN_THRESHOLD]].sum(axis=1) > 0
    )
    children_config = [
        c for c in inputs.household_composition_freq.columns if int(c.split(" ")[0]) > 0
    ]
    areas_no_house = (inputs.household_composition_freq[children_config]).sum(
        axis=1
    ) == 0.0

    # assert len(input_dict['household_composition_freq'][(areas_no_house) & (areas_with)]) == 0

    areas_with = (
        inputs.age_freq[inputs.age_freq.columns[CHILDREN_THRESHOLD:OLD_THRESHOLD]].sum(
            axis=1
        )
        > 0
    )
    adult_config = [
        c for c in inputs.household_composition_freq.columns if int(c.split(" ")[2]) > 0
    ]
    areas_no_house = (inputs.household_composition_freq[adult_config]).sum(
        axis=1
    ) == 0.0

    assert (
        len(inputs.household_composition_freq.loc[(areas_no_house) & (areas_with)]) == 0
    )


if __name__ == "__main__":
    test_enough_houses()
