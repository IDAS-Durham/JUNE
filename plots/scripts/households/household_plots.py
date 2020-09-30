import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
from collections import defaultdict
import argparse
import os
import mpu
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from june import paths

default_size_nr_file = paths.data_path / "input/households/household_size_per_area.csv"
default_couples_age_difference_filename = (
    paths.data_path / "input/households/couples_age_difference.csv"
)

default_parent_kid_age_difference_filename = (
    paths.data_path / "input/households/parent_kid_age_difference.csv"
)


class HouseholdPlots:
    def __init__(self, world):
        self.world = world

    def load_household_data(
        self, household_size_per_area_filename=default_size_nr_file,
    ):
        "Loading household data for plotting"

        self.household_sizes_per_area_data = pd.read_csv(
            household_size_per_area_filename
        )
        self.household_sizes_per_area_data.set_index("geography", inplace=True)
        self.couples_age_diff_data = pd.read_csv(
            default_couples_age_difference_filename, index_col=0
        )
        self.children_age_diff_data = pd.read_csv(
            default_parent_kid_age_difference_filename, index_col=0
        )

    def plot_household_sizes(self):
        "Plotting the size of households"
        # JUNE
        JUNE_household_sizes = defaultdict(int)
        n_households = 0
        for household in self.world.households:
            if household.type == "communal" or household.n_residents == 0:
                continue
            n_households += 1
            if household.n_residents > 8:
                n_residents = 8
            else:
                n_residents = household.n_residents
            JUNE_household_sizes[n_residents] += 1

        for key in JUNE_household_sizes:
            JUNE_household_sizes[key] = JUNE_household_sizes[key] / n_households * 100
        # data
        world_areas = [area.name for area in self.world.areas]
        household_sizes_data = self.household_sizes_per_area_data.loc[world_areas]
        n_households_data = household_sizes_data.values.sum()
        sizes_all_world = household_sizes_data.sum(axis=0) * 100 / n_households_data
        sizes_all_world_dict = {
            key: sizes_all_world[str(key)] for key in JUNE_household_sizes
        }

        f, ax = plt.subplots()
        ax.bar(
            JUNE_household_sizes.keys(),
            JUNE_household_sizes.values(),
            alpha=0.7,
            label="NOMIS sizes",
        )
        ax.bar(
            sizes_all_world_dict.keys(),
            sizes_all_world_dict.values(),
            alpha=0.7,
            label="JUNE sizes",
        )
        ax.set_xlabel("Household size")
        ax.set_ylabel("Frequency [\%]")
        ax.legend()
        return ax

    def plot_household_probability_matrix(self, bin_size=5):
        """
        Plots the probability of a person living with another person.
        """
        age_bins = np.arange(0, 100, bin_size)
        probability_matrix = np.zeros((int(100 / bin_size), int(100 / bin_size)))
        for person in self.world.people:
            for mate in person.residence.people:
                if mate == person:
                    continue
                person_age_bin = np.searchsorted(age_bins, person.age) - 1
                mate_age_bin = np.searchsorted(age_bins, mate.age) - 1
                probability_matrix[person_age_bin][mate_age_bin] += 1
        probability_matrix = probability_matrix / np.sum(probability_matrix, axis=0)
        f, ax = plt.subplots()
        cm = ax.pcolormesh(
            np.arange(0, 100, bin_size),
            np.arange(0, 100, bin_size),
            probability_matrix.T,
            norm=LogNorm(vmin=1e-4, vmax=1),
        )
        cbar = plt.colorbar(cm, ax=ax)
        cbar.set_label("Probability of living together", rotation=-90, labelpad=15)
        ax.set_xlabel("Person's age")
        ax.set_ylabel("Housemate's age")
        return ax

    def _compute_couples_age_difference(self):
        age_difference_couples = []
        for household in self.world.households:
            if household.type in ["family", "nokids"]:
                first_adult = None
                second_adult = None
                for person in household.people:
                    if person.age > 18:
                        if not first_adult:
                            first_adult = person
                        elif not second_adult:
                            second_adult = person
                        else:
                            break
                if first_adult is not None and second_adult is not None:
                    if first_adult.sex == "m":
                        age_diff = second_adult.age - first_adult.age
                    else:
                        age_diff = first_adult.age - second_adult.age
                    if -25 < age_diff < 25:
                        age_diff = min(20, max(-20, age_diff))
                        age_difference_couples.append(age_diff)
        return age_difference_couples

    def _compute_children_parent_age_difference(self):
        age_differences_first_kid = []
        age_differences_second_kid = []
        for household in self.world.households:
            if household.type == "family":
                mother = None
                father = None
                kids = []
                kids_ages = []
                for person in household.people:
                    if 18 < person.age < 60:
                        if person.sex == "m":
                            father = person
                        else:
                            mother = person
                    if person.age < 18:
                        kids.append(person)
                        kids_ages.append(person.age)
                if not kids_ages:
                    continue
                oldest_kid = np.array(kids)[np.argmax(kids_ages)]
                youngest_kid = np.array(kids)[np.argmin(kids_ages)]
                if mother is not None:
                    first_kid_age_diff = mother.age - oldest_kid.age
                    age_differences_first_kid.append(first_kid_age_diff)
                    second_kid_age_diff = mother.age - youngest_kid.age
                    age_differences_second_kid.append(second_kid_age_diff)
                elif father is not None:
                    first_kid_age_diff = father.age - oldest_kid.age
                    age_differences_first_kid.append(first_kid_age_diff)
                    second_kid_age_diff = father.age - youngest_kid.age
                    age_differences_second_kid.append(second_kid_age_diff)
                else:
                    continue
        return age_differences_first_kid, age_differences_second_kid

    def plot_household_age_differences(self):
        age_difference_couples = self._compute_couples_age_difference()
        (
            age_differences_first_kid,
            age_differences_second_kid,
        ) = self._compute_children_parent_age_difference()
        f, ax = plt.subplots(1, 3, sharey=True)
        ax[0].hist(age_difference_couples, density=True, label="JUNE", bins=20)
        ax[0].set_xlabel("Couples' age difference")
        ax[0].set_ylabel("Frequency [\%]")
        ax[0].plot(
            self.couples_age_diff_data.index,
            self.couples_age_diff_data.values,
            linewidth=3,
            label="census"
        )
        ax[0].set_xlim(-15, 15)
        ax[0].legend()

        ax[1].hist(age_differences_first_kid, density=True, label="JUNE", bins=20)
        ax[1].plot(
            self.children_age_diff_data.index,
            self.children_age_diff_data["1"],
            linewidth=3,
            label="census"
        )
        ax[1].set_xlabel("Parent - first child age difference")
        ax[1].set_xlim(18, 60)
        ax[1].legend()

        ax[2].hist(age_differences_second_kid, density=True, label="JUNE", bins=20)
        ax[2].plot(
            self.children_age_diff_data.index,
            self.children_age_diff_data["2"],
            linewidth=3,
            label="census"
        )
        ax[2].set_xlabel("Parent - second child age difference")
        ax[2].set_xlim(18, 60)
        ax[2].legend()
        plt.subplots_adjust(wspace=0, hspace=0)
        return f, ax
