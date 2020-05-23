import numpy as np
import json
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
from collections import defaultdict
from june.logger_simulation import Logger


default_shape_file_data_path = "/home/arnau/uk_msoa_shapefile/Middle_Layer_Super_Output_Areas__December_2011__Boundaries.shp"

default_area_conversion_data_path = (
    "/home/arnau/code/JUNE/data/processed/geographical_data/oa_msoa_region.csv"
)


class Plotter:
    def __init__(self, data: dict, load_shape_files=True):
        self.data = data
        if load_shape_files:
            self.load_shape_files()
            self.load_area_conversion()

    @classmethod
    def from_logger(cls, logger: Logger):
        return cls(logger.data_dict)

    @classmethod
    def from_json_file(cls, json_file_path: str):
        with open(json_file_path, "r") as f:
            data = json.load(f)
        return cls(data)

    def load_shape_files(
        self, shape_file_data_path: str = default_shape_file_data_path
    ):
        self.shape_df = gpd.read_file(shape_file_data_path)
        self.shape_df.set_index("msoa11cd", inplace=True)

    def load_area_conversion(
        self, area_conversion_data_path: str = default_area_conversion_data_path
    ):
        self.area_conversion_df = pd.read_csv(area_conversion_data_path, index_col=0)

    def plot_map_of_infected(self, hour, save_folder=None, vmin=None, vmax=None):
        hour = int(hour)
        infected_dict = defaultdict(int)
        for area in self.data:
            if area[0] != "E":
                continue
            data_area_time = self.data[area][str(hour)]
            infected = data_area_time["infected"]
            total = data_area_time["susceptible"] + data_area_time["recovered"] + data_area_time["infected"]
            area = self.area_conversion_df.loc[area].msoa
            infected_dict[area] += infected / total
        data_df = pd.DataFrame.from_dict({"areas" : list(infected_dict.keys()), "infected" : list(infected_dict.values())}).set_index("areas")
        areas_geometry = self.shape_df.loc[list(infected_dict.keys())]["geometry"]
        data_df["geometry"] = areas_geometry
        data_df = gpd.GeoDataFrame(data_df)
        fig, ax = plt.subplots()
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        data_df.plot(column="infected", legend=True, ax=ax, vmin=vmin, vmax=vmax)
        if save_folder is not None:
            fig.savefig(f"{save_folder}/time_{hour:04d}.png", dpi=200)
            plt.close("all")

    def save_map_of_infected_all_times(self, save_folder):
        vmin = 0
        vmax = 0.1
        hours = list(self.data[list(self.data.keys())[0]].keys())
        for hour in hours:
            self.plot_map_of_infected(hour, save_folder=save_folder, vmin=vmin, vmax=vmax)
