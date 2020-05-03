import numpy as np

from covid.commute import RegionalGenerator


class OArea:
    """
    Stores information about the area, like the total population
    number, universities, etc.
    """

    def __init__(
        self,
        world,
        coordinates,
        pcd,
        oarea,
        msoarea,
        n_residents,
        n_households,
        census_freq,
    ):
        self.world = world
        self.coordinates = coordinates  # Lon. & Lat
        self.pcd = pcd                  # Postcode
        self.name = oarea               # Output Area
        self.msoarea = msoarea          # Middle Super Output Area
        # distributions for distributing people
        self.census_freq = census_freq
        self.check_census_freq_ratios()
        self.n_residents = int(n_residents)
        self.n_households = n_households
        # collect groups
        self.people = []
        for relevant_groups in world.relevant_groups:
            setattr(self, relevant_groups, [])

    @property
    def regional_commute_generator(self) -> RegionalGenerator:
        """
        Object that generates modes of transport randomly weighted by census data
        """
        return self.world.commute_generator.regional_gen_from_msoarea(
            self.msoarea
        )

    def check_census_freq_ratios(self):
        for key in self.census_freq.keys():
            try:
                assert np.isclose(
                    np.sum(self.census_freq[key].values), 1.0, atol=0, rtol=1e-5
                )
            except AssertionError:
                raise ValueError(f"area {self.name} key {key}, ratios not adding to 1")


class OAreas:
    def __init__(self, world):
        self.world = world
        self.members = []
        self.names_in_order = None  # for fast search
