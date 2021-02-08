import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
from collections import defaultdict
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

import geopandas as gp
import geoplot as gplt
import geoplot.crs as gcrs

from june import paths

default_super_areas_foldername = paths.data_path / "plotting/super_area_boundaries/"

default_socioeconomic_index_filename = (
    paths.data_path / "input/demography/socioeconomic_index.csv"
)

default_area_to_super_area_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)
default_population_area_filename = (
    paths.data_path / "input/demography/age_structure_single_year.csv"
)

ethnicity_england = {
    "A": 45281142,
    "B": 1192879,
    "C": 4143403,
    "D": 1846614,
    "E": 548418,
}
n = sum(ethnicity_england.values())
for key in ethnicity_england:
    ethnicity_england[key] = ethnicity_england[key] / n * 100


class DemographyPlots:
    """
    Class for plotting demography related plots
    
    Parameters
    ----------
    world
        Preloaded world which can also be passed from the master plotting script
    """

    def __init__(self, world, colors):
        self.world = world
        self.colors = colors

    def plot_age_distribution(self):
        "Plotting age pyramid"

        male_ages = []
        female_ages = []
        for person in self.world.people:
            if person.sex == "f":
                female_ages.append(person.age)
            else:
                male_ages.append(person.age)

        male_counts, bins = np.histogram(
            male_ages, bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150]
        )
        female_counts, bins = np.histogram(
            female_ages, bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150]
        )

        ages = [
            "0-9",
            "10-19",
            "20-29",
            "30-39",
            "40-49",
            "50-59",
            "60-69",
            "70-79",
            "80-89",
            "90-99",
            "100+",
        ]

        data = {
            "Age": ages,
            "Male": (np.array(male_counts) / np.sum(male_counts)) * 100,
            "Female": (np.array(female_counts) / np.sum(female_counts)) * 100,
        }

        df = pd.DataFrame(data)

        y = range(0, len(df))
        x_male = df["Male"]
        x_female = df["Female"]

        fig, ax = plt.subplots(ncols=2, sharey=True, figsize=(6, 4))
        ax[0].barh(y, x_male, align="center", color=self.colors["male"])
        ax[0].set_ylabel("Ages")
        ax[0].set_xlabel("Males [\%]")
        ax[0].set(yticks=y, yticklabels=df["Age"])
        ax[0].invert_xaxis()
        ax[1].barh(y, x_female, align="center", color=self.colors["female"])
        ax[1].set_xlabel("Females [\%]")
        plt.subplots_adjust(wspace=0, hspace=0)

        return fig, ax

    def plot_population_density(
        self, super_areas_foldername=default_super_areas_foldername,
    ):

        super_areas = gp.read_file(super_areas_foldername)

        super_areas = super_areas.to_crs(epsg=3395)

        super_area_names = []
        for super_area in self.world.super_areas:
            super_area_names.append(super_area.name)
        super_area_names = np.array(super_area_names)

        world_super_areas = super_areas[super_areas["msoa11cd"].isin(super_area_names)]

        super_area_population = []
        for super_area in list(world_super_areas["msoa11cd"]):
            loc = np.where(super_area_names == super_area)[0][0]
            super_area_population.append(len(self.world.super_areas[loc].people))

        world_super_areas["area"] = world_super_areas["geometry"].area / 10 ** 6

        world_super_areas["population"] = super_area_population

        area_km = list(world_super_areas["area"])

        super_area_population = np.array(super_area_population)
        area_km = np.array(area_km)
        population_area = super_area_population / area_km

        fig, ax = plt.subplots()
        ax.hist(population_area, color=self.colors["JUNE"])
        ax.set_xlabel("People per sq. km")
        ax.set_ylabel("Frequency")

        return ax

    def plot_ethnicity_distribution(self):
        ethnicities = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}
        for person in self.world.people:
            ethnicities[person.ethnicity] += 1 / len(self.world.people) * 100
        ratios = {}
        for key in ethnicities:
            ratios[key] = ethnicities[key] / ethnicity_england[key]
        fig, ax = plt.subplots()
        ax.bar(ratios.keys(), ratios.values(), alpha=1.0, color=self.colors["JUNE"])
        # ax.set_title("Ethnicity distribution ratios compared to England average.")
        ax.legend()
        ax.set_xlabel("Ethnicity")
        ax.set_ylabel("Ratio")
        ax.axhline(1, linestyle="--", color="black")
        return ax

    @staticmethod  # so can call on any set of super areas.
    def process_socioeconomic_index_for_super_areas(
        list_of_super_areas,
        socioeconomic_index_filename=default_socioeconomic_index_filename,
        super_areas_foldername=default_super_areas_foldername,
    ):

        super_areas = gp.read_file(super_areas_foldername)
        super_areas = super_areas.to_crs(epsg=4326)
        super_areas = super_areas.query("msoa11cd in @list_of_super_areas")

        socioeconomic_index = pd.read_csv(socioeconomic_index_filename)
        socioeconomic_index = socioeconomic_index.query("msoa in @list_of_super_areas")

        sei_mean = (
            socioeconomic_index.groupby("msoa")["iomd_centile"]
            .mean()
            .rename("centile_mean")
        )
        sei_std = (
            socioeconomic_index.groupby("msoa")["iomd_centile"]
            .std()
            .rename("centile_std")
        )

        super_areas = pd.merge(
            left=super_areas,
            right=sei_mean,
            left_on="msoa11cd",
            right_index=True,
            how="inner",
            validate="1:1",
        )
        super_areas = pd.merge(
            left=super_areas,
            right=sei_std,
            left_on="msoa11cd",
            right_index=True,
            how="inner",
            validate="1:1",
        )

        return super_areas

    def process_socioeconomic_index_for_world(
        self,
        socioeconomic_index_filename=default_socioeconomic_index_filename,
        super_areas_foldername=default_super_areas_foldername,
    ):
        list_of_super_areas = [super_area.name for super_area in self.world.super_areas]

        super_areas = self.process_socioeconomic_index_for_super_areas(
            list_of_super_areas,
            socioeconomic_index_filename=default_socioeconomic_index_filename,
            super_areas_foldername=default_super_areas_foldername,
        )
        return super_areas

    @staticmethod
    def plot_socioeconomic_index(super_areas, column):
        fig, ax = plt.subplots(figsize=(7, 5))
        gplt.choropleth(
            super_areas,
            hue=column,
            cmap="Reds",
            legend=True,
            edgecolor="black",
            ax=ax,
            linewidth=0.1,
        )

        return ax

    def plot_age_distribution_comparison(
        self,
        area_super_area_filename=default_area_to_super_area_filename,
        population_filename=default_population_area_filename,
    ):
        area_to_super_area = pd.read_csv(area_super_area_filename)
        area_to_super_area.set_index("region", inplace=True)
        population = pd.read_csv(population_filename)
        population.set_index("output_area", inplace=True)
        regions_to_compare = ["London", "North East", "England"]
        f, ax = plt.subplots(1, len(regions_to_compare), figsize=(7, 2), sharex=True, sharey=True)
        colors = [self.colors[color] for color in ["general_1", "general_2", "general_3"]]
        for i, region in enumerate(regions_to_compare):
            if region == "England":
                filt = population.index.str.startswith("E")
                population_region = population.loc[filt]
            else:
                population_region = population.loc[
                    area_to_super_area.loc[region].area.values
                ]
            population_region = population_region.sum(axis=0) 
            keys = np.array(population_region.index, dtype=np.int)
            values = np.array(population_region.values / np.sum(population_region.values) * 100, dtype=np.float)
            ax[i].bar(
                keys,
                values,
                width=1,
                color = colors[i]
            )
            ax[i].set_xlabel("Age")
            ax[i].set_title(region)
        ax[0].set_ylabel("Frequency [\%]")
        plt.subplots_adjust(wspace=0, hspace=0)
        return ax
