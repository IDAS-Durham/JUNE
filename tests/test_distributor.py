import numpy as np
import os
from covid.inputs import create_input_df
from covid.classes import World, Person, Postcode, Household
from covid.distributor import populate_world


def test_global():

    census_df = create_input_df()
    census_df = census_df.sample(n=20)
    world = World(census_df)
    populate_world(world)

    n_residents_est = sum(
        [world.postcodes[i].n_residents for i in range(len(world.postcodes))]
    )
    n_residents = census_df["n_residents"].sum()

    assert n_residents == n_residents_est

    n_residents_est = sum(
        [len(world.postcodes[i].people) for i in range(len(world.postcodes))]
    )

    assert n_residents == n_residents_est

    n_households_est = sum(
        [world.postcodes[i].n_households for i in range(len(world.postcodes))]
    )
    n_households = census_df["n_households"].sum()

    assert n_households == n_households_est

    # n_households_est = sum(
    #    [len(world.postcodes[i].households) for i in range(len(world.postcodes))]
    # )
    # assert n_households == n_households_est


def test_per_postcode():

    census_df = create_input_df()
    census_df = census_df.sample(n=20)
    world = World(census_df)
    populate_world(world)

    n_residents_est = [
        world.postcodes[i].n_residents for i in range(len(world.postcodes))
    ]

    np.testing.assert_equal(n_residents_est, census_df["n_residents"].values)

    n_households_est = [
        world.postcodes[i].n_households for i in range(len(world.postcodes))
    ]

    np.testing.assert_equal(n_households_est, census_df["n_households"].values)


def test_frequencies():

    census_df = create_input_df()
    census_df = census_df.sample(n=20)
    world = World(census_df)
    populate_world(world)

    frequencies = []
    for i in world.postcodes.keys():
        freq = 0
        for j in world.postcodes[i].people.keys():
            freq += world.postcodes[i].people[j].sex
        freq /= world.postcodes[i].n_residents
        frequencies.append(freq)
    frequencies = np.asarray(frequencies)

    np.testing.assert_allclose(frequencies, census_df["females"].values, rtol=1e-1)


if __name__ == "__main__":
    test_frequencies()
