import numpy as np
import os


def test_global(world_ne):
    """
    test number of residents (people living in houses) is the same as overall real UK population (from census)
    test overall number of people in the simulation is also the UK population (from census)
    """

    inputs = world_ne.inputs

    n_residents_est = sum(
        [world_ne.areas.members[i].n_residents for i in range(len(world_ne.areas.members))]
    )
    n_residents = inputs.n_residents.sum()

    assert n_residents == n_residents_est

    n_residents_est = sum(
        [len(world_ne.areas.members[i].people) for i in range(len(world_ne.areas.members))]
    )

    assert n_residents == n_residents_est


def test_per_area():
    """
    test number of residents per Output Area is the real one (from census)
    """

    inputs = world_ne.inputs

    n_residents_est = [
        world_ne.areas.members[i].n_residents for i in range(len(world_ne.areas.members))
    ]

    np.testing.assert_equal(n_residents_est, inputs.n_residents.values)


def compute_n_samples(world_ne, attribute):
    print(attribute)
    frequencies = []
    decoder = getattr(world_ne.inputs, "decoder_" + attribute)
    for i in range(len(world_ne.areas.members)):
        freq = np.zeros(len(decoder))
        if "house" not in attribute:
            for j in range(len(world_ne.areas.members[i].people)):
                if attribute == "age":
                    attribute = "nomis_bin"
                freq[getattr(world_ne.areas.members[i].people[j], attribute)] += 1
            # freq /= world_ne.areas[i].n_residents
        else:
            for j in range(len(world_ne.areas.members[i].households)):
                print(getattr(world_ne.areas.members[i].households[j], attribute))
                freq[getattr(world_ne.areas.members[i].households[j], attribute)] += 1
            # freq /= world_ne.areas[i].n_households

        frequencies.append(freq)
    frequencies = np.asarray(frequencies)
    assert frequencies.shape == (len(world_ne.areas.members), len(decoder))
    return frequencies


def test_frequencies(world_ne):
    inputs = world_ne.inputs

    for key, value in census_dict_safe.items():
        if "freq" in key:
            attribute = key.split("_")
            attribute = "_".join(attribute[:-1])
            frequencies = compute_n_samples(world_ne, attribute)
            if "house" in key:
                n_samples = census_dict_safe[key].mul(
                    census_dict_safe["n_households"], axis=0
                )
            else:
                n_samples = census_dict_safe[key].mul(
                    census_dict_safe["n_residents"], axis=0
                )
            n_samples_total = n_samples.values.sum(axis=0)
            n_samples_est = np.sum(frequencies, axis=0)
            atol_matrix = n_samples_total * (1.0 / np.sqrt(n_samples_total))
            atol_matrix = np.where(atol_matrix == np.inf, 0.0, atol_matrix)

            for i in range(len(n_samples_est)):
                np.testing.assert_allclose(
                    n_samples_total[i], n_samples_est[i], atol=atol_matrix[i]
                )


if __name__ == "__main__":
    test_global()
    test_frequencies()
