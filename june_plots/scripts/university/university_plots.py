from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd
import contextily as ctx
import geopandas as gpd

from june.paths import data_path

# default_super_areas_shapefile = list(
#    (data_path / "plotting/super_area_boundaries").glob("*.shp")
# )[0]
default_area_centroids_filename = data_path / "input/geography/area_centroids.csv"
newcastle_shapefiles = list(
    (data_path / "plotting/newcastle_shapefiles").glob("*.shp")
)[0]
county_durham_shapefiles = list(
    (data_path / "plotting/county_durham_oa_shapefiles").glob("*.shp")
)[0]
england_shapefiles = (
    "/home/arnau/Downloads/england_oa_shapefiles/infuse_oa_lyr_2011_clipped.shp"
)


class UniversityPlots:
    def __init__(
        self, world,
    ):
        self.world = world
        # self.shapefile = newcastle_shapefiles
        self.shapefile = county_durham_shapefiles 
        self.area_centroids = pd.read_csv(default_area_centroids_filename, index_col=0)
        # uni_ukprn = 10007799
        uni_ukprn = 10007143
        # uni_ukprn = 10007161
        uni = [
            university
            for university in self.world.universities
            if university.ukprn == uni_ukprn
        ]
        self.no_uni = False
        if not uni:
            print("No uni plots available in this world (needs Newcastle)")
            self.no_uni = True
        else:
            self.uni = uni[0]

    def load_university_data(self):
        self.uni_students = []
        for person in self.world.people:
            if person.primary_activity is not None:
                if (
                    person.primary_activity.group.spec == "university"
                    and person.primary_activity.group.ukprn == self.uni.ukprn
                ):
                    self.uni_students.append(person)

        for university in self.world.universities:
            university.clear()

    def plot_students_household_type_histogram(self):
        household_types = defaultdict(int)
        for student in self.uni_students:
            household_type = student.residence.group.type
            if household_type != "communal":
                household_type = "non-communal"
            household_types[household_type] += 1
        total = sum(household_types.values())
        to_plot = {
            cat: household_types[cat] / total * 100 for cat in household_types
        }
        f, ax = plt.subplots()
        ax.bar(to_plot.keys(), to_plot.values())
        ax.set_xlabel("Household type")
        ax.set_ylabel("Frequency [\%]")
        return ax

    def plot_where_students_live(self):
        """
        Map plot of where students live around the university.
        If Durham is in the world, then it plots durham uni,
        otherwise the first uni it finds.
        """
        area_populations = defaultdict(int)
        for student in self.uni_students:
            area_populations[student.area.name] += 1
        self.world_map = gpd.read_file(self.shapefile)
        self.world_map.set_index("code", inplace=True)
        counts = []
        areas = []
        for area, row in self.world_map.iterrows():
            if area in area_populations:
                if area_populations[area] > 0:
                    counts.append(area_populations[area])
                    areas.append(area)
        toplot = self.world_map.loc[areas]
        toplot["counts"] = counts
        fig, ax = plt.subplots()
        toplot = toplot.to_crs(epsg=3857)
        toplot.plot('counts', ax=ax, alpha=0.7, cmap="viridis", norm=LogNorm())
        ax.set_xlim(-178000, -172000)
        ax.set_ylim(7.315e6, 7.320e6)
        ctx.add_basemap(ax, source=ctx.providers.Stamen.Toner, attribution_size=5)
        ax.xaxis.set_major_formatter(plt.NullFormatter())
        ax.yaxis.set_major_formatter(plt.NullFormatter())
        uni_centroid = self.area_centroids.loc[self.uni.area.name].values
        ax.scatter(*uni_centroid, color="red", marker="*")
        return ax
