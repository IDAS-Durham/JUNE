import numpy as np

from covid.commute import RegionalGenerator


class Area:
    """
    Stores information about the area, like the total population
    number, universities, etc.
    """

    def __init__(
        self, world, oarea, msoarea, n_residents, n_households, census_freq, coordinates
    ):
        self.world = world
        self.name = oarea
        self.msoarea = msoarea
        self.n_residents = int(n_residents)
        self.n_households = n_households
        self.census_freq = census_freq
        self.check_census_freq_ratios()
        self.people = []
        self.households = []
        self.coordinates = coordinates

    @property
    def regional_commute_generator(self) -> RegionalGenerator:
        """
        Object that generates modes of transport randomly weighted by census data
        """
        return self.world.commute_generator.for_msoarea(self.msoarea)

    def check_census_freq_ratios(self):
        for key in self.census_freq.keys():
            try:
                assert np.isclose(
                    np.sum(self.census_freq[key].values), 1.0, atol=0, rtol=1e-5
                )
            except AssertionError:
                raise ValueError(f"area {self.name} key {key}, ratios not adding to 1")


class Areas:
    def __init__(self, world):
        self.world = world
        self.members = []
