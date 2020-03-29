import numpy as np
import os
from covid.inputs import create_input_dict
from covid.classes import World, Person, Postcode, Household
from covid.distributor import populate_world


def test_global():

    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=20,random_state=111)
    census_dict_safe = census_dict.copy()
    world = World(census_dict)
    populate_world(world)

    n_residents_est = sum(
        [world.postcodes[i].n_residents for i in range(len(world.postcodes))]
    )
    n_residents = census_dict_safe["n_residents"].sum()

    assert n_residents == n_residents_est

    n_residents_est = sum(
        [len(world.postcodes[i].people) for i in range(len(world.postcodes))]
    )

    assert n_residents == n_residents_est

    n_households_est = sum(
        [world.postcodes[i].n_households for i in range(len(world.postcodes))]
    )
    n_households = census_dict_safe["n_households"].sum()

    assert n_households == n_households_est

    # n_households_est = sum(
    #    [len(world.postcodes[i].households) for i in range(len(world.postcodes))]
    # )
    # assert n_households == n_households_est


def test_per_postcode():

    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=20,random_state=111)
    census_dict_safe = census_dict.copy()

    world = World(census_dict)
    populate_world(world)

    n_residents_est = [
        world.postcodes[i].n_residents for i in range(len(world.postcodes))
    ]

    np.testing.assert_equal(n_residents_est, census_dict_safe["n_residents"].values)

    n_households_est = [
        world.postcodes[i].n_households for i in range(len(world.postcodes))
    ]

    np.testing.assert_equal(n_households_est, census_dict_safe["n_households"].values)

# TODO: GENERALIZE FOR ANY FREQUENCY, NOT NECESSARILY BINARY
def get_frequency(world, attribute):
    frequencies = []
    for i in world.postcodes.keys():
        freq = 0
        for j in world.postcodes[i].people.keys():
            freq += getattr(world.postcodes[i].people[j], attribute)
        freq /= world.postcodes[i].n_residents
        frequencies.append(freq)
    frequencies = np.asarray(frequencies)
    return frequencies

def test_frequencies():

    census_dict = create_input_dict()
    for key, value in census_dict.items():
        census_dict[key] = census_dict[key].sample(n=20,random_state=111)
    census_dict_safe = census_dict.copy()

    world = World(census_dict)
    populate_world(world)

    for key, value in census_dict_safe.items():
        if 'freq' in key:
            print(key)
            frequencies = get_frequency(world, key)
            if key == 'sex': # replace by if binary, compute frequency of postive class (saved in person or sowhere)
                np.testing.assert_allclose(frequencies, census_dict_safe[key]["females"].values, rtol=1e-1)
            else:
    
            for column in census_dict_safe[key].columns:

if __name__ == "__main__":
    test_global()
