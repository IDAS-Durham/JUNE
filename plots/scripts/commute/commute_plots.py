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

default_super_areas_foldername = (
    paths.data_path / "plotting/super_area_boundaries/"
)


class CommutePlots:
    """
    Class for plotting commute related plots
    
    Parameters
    ----------
    world
        Preloaded world which can also be passed from the master plotting script
    """

    def __init__(self, world):
        self.world = world

    def plot_internal_external_numbers(self):
        "Plotting number of internal and external commuters across all cities in World"

        internal_commuters = []
        external_commuters = []
        names = []
        for city in world.cities:
            external = 0
            for station in city.stations:
                external += len(station.commuter_ids)

            internal = len(city.commuter_ids)
            if external != 0 and internal != 0:
                external_commuters.append(external)
                names.append(city.name)
                internal_commuters.append(internal)

        internal_commuters = np.array(internal_commuters)
        external_commuters = np.array(external_commuters)

        x = np.arange(len(names))  # the label locations
        width = 0.35  # the width of the bars

        f, ax = plt.subplots()
        ax.bar(x, internal_commuters, width/2, label = 'Internal commuters')
        ax.bar(x - width/2, external_commuters, width/2, label = 'External commuters')
        ax.bar(x + width/2, external_commuters+internal_commuters, width/2, label = 'Total commuters')
        ax.set_ylabel('Number of people')
        ax.set_xticks(x)
        ax.set_xticklabels(names)
        ax.legend()
        plt.xticks(rotation=45)

        return ax

    def process_internal_external_areas(
            self,
            super_areas_foldername = default_super_areas_foldername,
            city_to_plot = 'Newcastle upon Tyne',
    ):
        "Plotting internal and external super areas and number of commuters"

        super_areas = gp.read_file(super_areas_foldername)

        super_areas = super_areas.to_crs(epsg=4326)

        plot_city = None

        for city in world.cities:
            if city.name == city_to_plot:
                plot_city = city
                break

        internal_commuters_ids = []
        external_commuters_ids = []
        commuters_ids = []
        for commuter in list(city.commuter_ids):
            internal_commuters_ids.append(commuter)
            commuters_ids.append(commuter)
        for station in city.stations:
            for commuter in list(station.commuter_ids):
                commuters_ids.append(commuter)
                external_commuters_ids.append(commuter)

        live_super_areas = []
        internal_super_areas = []
        external_super_areas = []
        for commuter_id in commuters_ids:
            live_super_areas.append(world.people[commuter_id].super_area.name)
        for commuter_id in internal_commuters_ids:
            internal_super_areas.append(world.people[commuter_id].super_area.name)
        for commuter_id in external_commuters_ids:
            external_super_areas.append(world.people[commuter_id].super_area.name)

        live_super_area_names, live_super_area_counts = np.unique(live_super_areas, return_counts=True)
        internal_super_area_names = np.unique(internal_super_areas)
        external_super_area_names = np.unique(external_super_areas)

        commute_areas = super_areas[super_areas['msoa11cd'].isin(live_super_area_names)]

        commute_areas['commuters'] = live_super_area_counts

        for idx, super_area in enumerate(live_super_area_names):
            commute_areas['commuters'][commute_areas['msoa11cd'] == super_area] = live_super_area_counts[idx]

        internal_commute_areas = commute_areas[commute_areas['msoa11cd'].isin(internal_super_area_names)]
        external_commute_areas = commute_areas[commute_areas['msoa11cd'].isin(external_super_area_names)]

        return internal_commute_areas, external_commute_areas

    def plot_commute_areas(self, commute_areas):

        fig, ax = plt.subplots()
        gplt.choropleth(
            commute_areas, hue='commuters',
            cmap='Reds', legend=True, edgecolor="black", ax=ax
        )

        return ax


    

    

    
