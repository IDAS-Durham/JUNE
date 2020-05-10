from enum import IntEnum

import numpy as np
import pandas as pd

from june.commute import RegionalGenerator
from june.groups.group import Group


class Area(Group):
    class GroupType(IntEnum):
        default = 0

    """
    Stores information about the area, like the total population
    number, universities, etc.

    Inherits from Group class since people living in the same area
    can have social interaction.
    """

    def __init__(
            self,
            coordinates: [float, float],
            name: str,
            super_area,
            n_residents: int,
            n_households: int,
            census_freq: dict,
            relevant_groups: list,
    ):
        super().__init__()
        self._name = name
        self.coordinates = np.array(coordinates)  # Lon. & Lat
        self.super_area = super_area
        # distributions for distributing people
        self.census_freq = census_freq
        self.check_census_freq_ratios()
        self.n_residents = int(n_residents)
        self.n_households = n_households
        self.carehome = None
        # collect groups (such as hospitals schools, ...)
        # people tag already taken ...
        # self.people = []
        for relevant_groups in relevant_groups:
            setattr(self, relevant_groups, [])

    @property
    def name(self):
        return self._name

    @property
    def regional_commute_generator(self) -> RegionalGenerator:
        """
        Object that generates modes of transport randomly weighted by census data
        """
        # TODO update for new code structure
        return self.world.commute_generator.regional_gen_from_msoarea(
            self.super_area
        )

    def check_census_freq_ratios(self):
        for key in self.census_freq.keys():
            try:
                assert np.isclose(
                    np.sum(self.census_freq[key].values), 1.0, atol=0, rtol=1e-5
                )
            except AssertionError:
                raise ValueError(f"area {self.name} key {key}, ratios not adding to 1")


class Areas:
    def __init__(
            self,
            n_residents: pd.DataFrame,
            age_freq: pd.DataFrame,
            decoder_age: dict,
            sex_freq: pd.DataFrame,
            decoder_sex: dict,
            household_composition_freq: pd.DataFrame,
            decoder_household_composition: dict,
            encoder_household_composition: dict,
    ):
        self.members = []
        self.area_tree = None
        self.names_in_order = None
        self.n_residents = n_residents
        self.age_freq = age_freq
        self.sex_freq = sex_freq
        self.household_composition_freq = household_composition_freq

        self.decoder_age = decoder_age
        self.decoder_sex = decoder_sex
        self.decoder_household_composition = decoder_household_composition
        self.encoder_household_composition = encoder_household_composition

    @classmethod
    def from_file(
            cls,
            n_residents_file: str,
            age_freq_file: str,
            sex_freq_file: str,
            household_composition_freq_file: str,
    ) -> "Areas":
        """
        Parameters
        ----------
        n_residents_file:
            Nr. of residents per area
        age_freq_file:
            Nr of people wihin age-range per area
        sex_freq_file:
            Nr of people per sec per area
        household_composition_freq_file:
            Nr. of household categories per area

        """
        n_residents = pd.read_csv(
            n_residents_file,
            names=["output_area", "n_residents"],
            header=0,
            index_col="output_area",
        )
        age_freq, decoder_age = Areas.read(age_freq_file)
        sex_freq, decoder_sex = Areas.read(sex_freq_file)
        (
            household_composition_freq,
            decoder_household_composition,
        ) = Areas.read(
            household_composition_freq_file
        )
        encoder_household_composition = {}
        for i, column in enumerate(household_composition_freq.columns):
            encoder_household_composition[column] = i

        return Areas(
            n_residents,
            age_freq,
            decoder_age,
            sex_freq,
            decoder_sex,
            household_composition_freq,
            decoder_household_composition,
            encoder_household_composition,
        )

    @staticmethod
    def read(filename: str):
        df = pd.read_csv(filename, index_col="output_area")
        freq = df.div(df.sum(axis=1), axis=0)
        decoder = {i: df.columns[i] for i in range(df.shape[-1])}
        return freq, decoder
