from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib import colors
import numpy as np
import pandas as pd
import contextily as ctx
import geopandas as gpd

from june.paths import data_path

default_area_centroids_filename = data_path / "input/geography/area_centroids.csv"
county_durham_shapefiles = list(
    (data_path / "plotting/county_durham_oa_shapefiles").glob("*.shp")
)[0]


class UniversityPlots:
    def __init__(
        self, world,
    ):
        self.world = world
        self.shapefile = county_durham_shapefiles
        self.area_centroids = pd.read_csv(default_area_centroids_filename, index_col=0)
        uni_ukprn = 10007143
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
        to_plot = {cat: household_types[cat] / total * 100 for cat in household_types}
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
        toplot["counts"] = counts / np.sum(counts) * 100
        fig, ax = plt.subplots()
        toplot = toplot.to_crs(epsg=3857)
        toplot.plot(
            "counts",
            ax=ax,
            alpha=0.7,
            cmap="viridis",
            legend=False,
            vmin=1, 
            vmax=4.5
        )
        ax.set_xlim(-178000, -172000)
        ax.set_ylim(7.315e6, 7.320e6)
        ctx.add_basemap(ax, source=ctx.providers.Stamen.Toner, attribution_size=5)
        ax.xaxis.set_major_formatter(plt.NullFormatter())
        ax.yaxis.set_major_formatter(plt.NullFormatter())
        uni_centroid = toplot.loc[self.uni.area.name]
        ax.scatter(
            uni_centroid.geometry.centroid.x,
            uni_centroid.geometry.centroid.y,
            marker="*",
            color="red",
        )
        ax.tick_params(left=False, labelleft=False, bottom=False, labelbottom=False)

        # colorbar
        norm = colors.Normalize(vmin=1, vmax=4)
        cbar = plt.cm.ScalarMappable(norm=norm, cmap="viridis")
        ax_cbar = fig.colorbar(cbar, ax=ax)
        ax_cbar.set_label("Fraction of students [\%]", rotation=-90, labelpad=20)
        yticklabels = ax_cbar.ax.get_yticklabels()
        yticklabels = list(map(str, yticklabels))
        yticklabels[-1] = r">4"
        ax_cbar.ax.set_yticklabels(yticklabels)
        # margins
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.margins(0, 0)
        return ax
