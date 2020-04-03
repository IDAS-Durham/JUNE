import numpy as np


class Area:
    """
    Stores information about the area, like the total population
    number, universities, etc.
    """

    def __init__(self, world, name, n_residents, n_households, census_freq, coordinates):
        self.world = world
        self.name = name
        self.n_residents = int(n_residents)
        self.n_households = n_households
        self.census_freq = census_freq
        self.check_census_freq_ratios()
        self.people = {}
        self.households = {}
        self.coordinates = coordinates

    def check_census_freq_ratios(self):
        for key in self.census_freq.keys():
            try:
                assert np.isclose(
                    np.sum(self.census_freq[key].values), 1.0, atol=0, rtol=1e-5
                )
            except AssertionError:
                raise ValueError(f"area {self.name} key {key}, ratios not adding to 1")

