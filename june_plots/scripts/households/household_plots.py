import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
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

default_hc_by_age_filename = paths.data_path / "plotting/hc_england_by_age.csv"


class HouseholdPlots:
    def __init__(self, world, colors):
        self.world = world
        self.colors = colors

    def load_household_data(
        self,
        household_size_per_area_filename=default_size_nr_file,
        hc_by_age_filename=default_hc_by_age_filename,
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
        self.hc_by_age = pd.read_csv(hc_by_age_filename)

    def plot_all_household_plots(self, save_dir):
        print("Loading household data")
        self.load_household_data()

        print("Plotting household sizes")
        household_sizes_plot = self.plot_household_sizes()
        household_sizes_plot.plot()
        plt.savefig(save_dir / "household_sizes.png", dpi=150, bbox_inches="tight")
        
        print("Plotting household size comparison to England avg.")
        household_sizes_ratios = self.plot_household_sizes_ratio_to_england()
        household_sizes_ratios.plot()
        plt.savefig(save_dir / "household_sizes_ratios.png", dpi=150, bbox_inches="tight")

        print("Plotting household probability matrix")
        household_probability_matrix = self.plot_household_probability_matrix()
        household_probability_matrix.plot()
        plt.savefig(
            save_dir / "household_prob_matrix.png", dpi=150, bbox_inches="tight"
        )

        print("Plotting household age differences")
        f, ax = self.plot_household_age_differences()
        plt.plot()
        plt.savefig(
            save_dir / "household_age_differences.png", dpi=150, bbox_inches="tight"
        )

        print("Plotting hc by age")
        hc_plot = self.plot_household_composition_by_age()
        hc_plot.plot()
        plt.savefig(
            save_dir / "household_composition_by_age.png", dpi=150, bbox_inches="tight"
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
        household_sizes_data = self.household_sizes_per_area_data.loc[world_areas].sum(
            axis=0
        )
        n_households_data = household_sizes_data.values.sum()
        household_sizes_data = household_sizes_data / n_households_data * 100
        sizes_all_world_dict = household_sizes_data.to_dict()
        sizes_all_world_dict_ordered = OrderedDict()
        for key in JUNE_household_sizes:
            sizes_all_world_dict_ordered[key] = sizes_all_world_dict[str(key)]

        f, ax = plt.subplots()
        ax.bar(
            sizes_all_world_dict_ordered.keys(),
            sizes_all_world_dict_ordered.values(),
            alpha=0.7,
            label="ONS sizes",
            color=self.colors['ONS']
        )
        ax.bar(
            JUNE_household_sizes.keys(),
            JUNE_household_sizes.values(),
            alpha=0.7,
            label="JUNE sizes",
            color=self.colors['JUNE']
        )
        ax.set_xlabel("Household size")
        ax.set_ylabel("Frequency [\%]")
        ax.legend()
        return ax

    def plot_household_sizes_ratio_to_england(self):
        "Plotting the size of households compared to england."
        # JUNE
        england_sizes = {
            1: 6666493,
            2: 7544404,
            3: 3437917,
            4: 2866800,
            5: 1028477,
            6: 369186,
            7: 88823,
            8: 61268,
        }
        n = sum(england_sizes.values())
        for key in england_sizes:
            england_sizes[key] = england_sizes[key] / n
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
            JUNE_household_sizes[key] = JUNE_household_sizes[key] / n_households
        # data
        ratios = {}
        for key in england_sizes:
            ratios[key] = JUNE_household_sizes[key] / england_sizes[key]
        f, ax = plt.subplots()
        ax.bar(
            ratios.keys(),
            ratios.values(),
            color=self.colors['JUNE'],
        )
        ax.set_title("Household size simulated world / England ratios..")
        ax.set_xlabel("Household size")
        ax.set_ylabel("Ratio")
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

        f, ax = plt.subplots(1, 3, sharey=True, figsize=(8, 3))
        ax[0].set_xlabel("Couples' age difference")
        ax[0].set_ylabel("Frequency [\%]")
        ax[0].plot(
            self.couples_age_diff_data.index,
            self.couples_age_diff_data.values,
            linewidth=2,
            label="ONS",
            color=self.colors['ONS']
        )
        ax[0].hist(
            age_difference_couples, density=True, label="JUNE", bins=20, alpha=0.7, color=self.colors['JUNE']
        )
        ax[0].set_xlim(-15, 15)
        ax[0].legend()

        ax[1].plot(
            self.children_age_diff_data.index,
            self.children_age_diff_data["1"],
            linewidth=2,
            label="ONS",
            color=self.colors['ONS']
        )
        ax[1].hist(
            age_differences_first_kid, density=True, label="JUNE", bins=30, alpha=0.7, color=self.colors['JUNE']
        )
        ax[1].set_xlabel("Parent - first child\nage difference")
        ax[1].set_xlim(15, 65)
        ax[1].legend()

        ax[2].plot(
            self.children_age_diff_data.index,
            self.children_age_diff_data["2"],
            linewidth=2,
            label="ONS",
            color=self.colors['ONS']
        )
        ax[2].hist(
            age_differences_second_kid, density=True, label="JUNE", bins=30, alpha=0.7, color=self.colors['JUNE']
        )
        ax[2].set_xlabel("Parent - second child\nage difference")
        ax[2].set_xlim(15, 66)
        ax[2].legend()
        plt.subplots_adjust(wspace=0, hspace=0)
        return f, ax

    def plot_household_composition_by_age(self):
        # data
        data_hc = pd.read_csv(default_hc_by_age_filename, index_col=0)
        data_hc = data_hc / data_hc.sum(axis=0)
        # june
        names = ["0-15", "16-24", "25-34", "35-49", "50-100"]
        june_hc = {
            htype: {age_range: 0 for age_range in names}
            for htype in ["single", "couple", "family", "other"]
        }
        for person in self.world.people:
            if person.residence.group.spec != "household":
                continue
            household = person.residence.group
            if household.type in ["family", "ya_parents"]:
                htype = "family"
            elif household.type in ["nokids", "old"]:
                if len(household.people) == 1:
                    htype = "single"
                else:
                    htype = "couple"
            elif household.type in ["student", "communal", "young_adults"]:
                htype = "other"
            if person.age <= 15:
                age_range = "0-15"
            elif person.age <= 24:
                age_range = "16-24"
            elif person.age <= 34:
                age_range = "25-34"
            elif person.age <= 49:
                age_range = "35-49"
            else:
                age_range = "50-100"
            june_hc[htype][age_range] += 1
        june_hc = pd.DataFrame.from_dict(june_hc)
        june_hc = june_hc / june_hc.sum(axis=0)

        f, ax = plt.subplots()
        totals = [
            i + j + k + l
            for i, j, k, l in zip(
                data_hc["single"],
                data_hc["couple"],
                data_hc["family"],
                data_hc["other"],
            )
        ]
        # plot
        barWidth = 0.25
        r = [0, 1, 2, 3, 4]
        # data bars
        single = [i / j * 100 for i, j in zip(data_hc["single"], totals)]
        couple = [i / j * 100 for i, j in zip(data_hc["couple"], totals)]
        family = [i / j * 100 for i, j in zip(data_hc["family"], totals)]
        other = [i / j * 100 for i, j in zip(data_hc["other"], totals)]
        ax.bar(
            r,
            single,
            color="C0",
            edgecolor="white",
            width=barWidth,
            label="ONS single",
            align="center",
        )
        # Create orange Bars
        ax.bar(
            r,
            couple,
            bottom=single,
            color="C1",
            align="center",
            edgecolor="white",
            width=barWidth,
            label="ONS couple",
        )
        # Create blue Bars
        ax.bar(
            r,
            family,
            bottom=[i + j for i, j in zip(single, couple)],
            color=f"C2",
            edgecolor="white",
            align="center",
            width=barWidth,
            label="ONS family",
        )
        ax.bar(
            r,
            other,
            bottom=[i + j + k for i, j, k in zip(single, couple, family)],
            color="C3",
            edgecolor="white",
            align="center",
            width=barWidth,
            label="ONS other",
        )
        # JUNE
        totals = [
            i + j + k + l
            for i, j, k, l in zip(
                june_hc["single"],
                june_hc["couple"],
                june_hc["family"],
                june_hc["other"],
            )
        ]
        # plot
        r = np.array([0.0, 1.0, 2.0, 3.0, 4.0]) + barWidth
        # june bars
        single = [i / j * 100 for i, j in zip(june_hc["single"], totals)]
        couple = [i / j * 100 for i, j in zip(june_hc["couple"], totals)]
        family = [i / j * 100 for i, j in zip(june_hc["family"], totals)]
        other = [i / j * 100 for i, j in zip(june_hc["other"], totals)]

        ax.bar(
            r,
            single,
            color="C0",
            edgecolor="white",
            width=barWidth,
            label="JUNE single",
            align="center",
            alpha=0.5,
        )
        # Create orange Bars
        ax.bar(
            r,
            couple,
            bottom=single,
            color="C1",
            align="center",
            edgecolor="white",
            width=barWidth,
            label="JUNE couple",
            alpha=0.5,
        )
        # Create blue Bars
        ax.bar(
            r,
            family,
            bottom=[i + j for i, j in zip(single, couple)],
            color=f"C2",
            edgecolor="white",
            align="center",
            width=barWidth,
            label="JUNE family",
            alpha=0.5,
        )
        ax.bar(
            r,
            other,
            bottom=[i + j + k for i, j, k in zip(single, couple, family)],
            color="C3",
            edgecolor="white",
            align="center",
            width=barWidth,
            label="JUNE other",
            alpha=0.5,
        )
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        plt.xticks(r - barWidth / 2, names)
        ax.set_ylabel("Household type")
        ax.set_xlabel("Age")

        return ax
