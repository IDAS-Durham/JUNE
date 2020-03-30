import numpy as np
import os
from covid.inputs import create_input_dict
from covid.classes import World, Person, Area, Household
from covid.distributor import populate_world


def test_global():

    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=5, random_state=111)
    census_dict_safe = census_dict.copy()
    world = World(census_dict)
    populate_world(world)

    n_residents_est = sum(
        [world.areas[i].n_residents for i in range(len(world.areas))]
    )
    n_residents = census_dict_safe["n_residents"].sum()

    assert n_residents == n_residents_est

    n_residents_est = sum(
        [len(world.areas[i].people) for i in range(len(world.areas))]
    )

    assert n_residents == n_residents_est

    n_households_est = sum(
        [world.areas[i].n_households for i in range(len(world.areas))]
    )
    n_households = census_dict_safe["n_households"].sum()

    assert n_households == n_households_est

    # n_households_est = sum(
    #    [len(world.areas[i].households) for i in range(len(world.areas))]
    # )
    # assert n_households == n_households_est


def test_per_area():

    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=5, random_state=111)
    census_dict_safe = census_dict.copy()

    world = World(census_dict)
    populate_world(world)

    n_residents_est = [
        world.areas[i].n_residents for i in range(len(world.areas))
    ]

    np.testing.assert_equal(n_residents_est, census_dict_safe["n_residents"].values)

    n_households_est = [
        world.areas[i].n_households for i in range(len(world.areas))
    ]

    np.testing.assert_equal(n_households_est, census_dict_safe["n_households"].values)


def compute_frequency(world, attribute):
    print(attribute)
    frequencies = []
    decoder = getattr(world, "decoder_" + attribute)
    for i in world.areas.keys():
        freq = np.zeros(len(decoder))
        if 'house' not in attribute:
            for j in world.areas[i].people.keys():
                freq[getattr(world.areas[i].people[j], attribute)] += 1
            freq /= world.areas[i].n_residents
        else:
            for j in world.areas[i].households.keys():
                freq[getattr(world.areas[i].households[j], attribute)] += 1
            freq /= world.areas[i].n_households

        frequencies.append(freq)
    frequencies = np.asarray(frequencies)
    assert frequencies.shape == (len(world.areas), len(decoder))
    return frequencies


def test_frequencies():

    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=5, random_state=111)
    census_dict_safe = census_dict.copy()

    world = World(census_dict)
    populate_world(world)

    for key, value in census_dict_safe.items():
        if "freq" in key:
            attribute = key.split("_")
            attribute = "_".join(attribute[:-1])
            frequencies = compute_frequency(world, attribute)
            np.testing.assert_allclose(
                frequencies,
                census_dict_safe[key].values,
                atol=1.0 / np.sqrt(census_dict_safe["n_residents"].min()),
            )

def test_lonely_children():
    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=2, random_state=111)
    census_dict_safe = census_dict.copy()

    world = World(census_dict)
    populate_world(world)
    attribute = 'age'
    decoder = getattr(world, "decoder_" + attribute)
    only_children = 0
    for i in world.areas.keys():
        for j in world.areas[i].households.keys():
            freq = np.zeros(len(decoder))
            for k in world.areas[i].households[j].residents.keys():
                freq[getattr(world.areas[i].households[j].residents[k], attribute)] += 1
                # if no adults, but at least one child
                if (np.sum(freq[5:]) == 0.) & (np.sum(freq[:5]) > 0.):
                    only_children += 1

    assert only_children == 0
if __name__ == "__main__":
    test_lonely_children()
