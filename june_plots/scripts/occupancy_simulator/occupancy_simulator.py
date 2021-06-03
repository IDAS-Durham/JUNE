import psutil
import os
import copy
import pickle
import time
import datetime as dt
import yaml
from collections import Counter, defaultdict, ChainMap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
import tables

from june.hdf5_savers import generate_world_from_hdf5
from june.groups.leisure import generate_leisure_for_config, SocialVenue
from june.groups.group.interactive import InteractiveGroup
from june.groups.school import _get_contacts_in_school
from june.groups import InteractiveSchool, InteractiveCompany, InteractiveHousehold
from june.groups import Group, Subgroup

#from june.epidemiology.infection.import HealthIndexGenerator
#from june.epidemiology.infection.seed import InfectionSeed, Observed2Cases
#from june.epidemiology.infection.import InfectionSelector, HealthIndexGenerator
from june.groups.travel import Travel
from june.policy import Policies
from june.records import Record, RecordReader
from june.records.event_records_writer import EventRecord
from june.demography import Person

from june.mpi_setup import mpi_rank, mpi_size, mpi_comm

from june import paths
from june.simulator import Simulator

class OccupancySimulator:

    def __init__(
        self, 
        simulator=None, 
        simulation_outputs_path=None,
        simulation_record=None,
        simulation_days=7,
    ):

        self.simulator = simulator
        self.simulation_record = simulation_record
        self.simulation_outputs_path = simulation_outputs_path
        self.simulation_outputs_path.mkdir(exist_ok=True, parents=True)

        self.simulation_days = simulation_days

        self.all_activities = [
            'medical_facility', 'residence', 'commute', 'primary_activity', 'leisure'
        ]
        if simulator is not None:
            self.world = self.simulator.world
            self.timer = self.simulator.timer
            self.initialise_occupancy_tracker()

    def initialise_occupancy_tracker(self):
        self.occupancy_tracker = (
            {supergroup[0].spec: [] for supergroup in self.world.supergroups if len(supergroup) > 0}
        )

    def global_operations(self,):
        pass

    def group_operations(self, interactive_group: InteractiveGroup):
        """operations for occupancy simulator"""
        self.track_occupancy(interactive_group)

    def track_occupancy(self, interactive_group: InteractiveGroup):
        #if isinstance(group, SocialVenue):
        occ = interactive_group.size #/ group.max_size
        self.occupancy_tracker[interactive_group.spec].append(
            (occ, interactive_group.group.id) #, group.super_area.region, group.super_area)
        )
            
    def record_output(self):
        if mpi_rank == 0:
            print(f"save output at {self.timer.date}")
        for venue_type in self.occupancy_tracker.keys():
            if len(self.occupancy_tracker[venue_type]) > 0:
                arr = np.array(list(self.occupancy_tracker[venue_type]))
                time = f"{self.timer.date.hour:02d}:{self.timer.date.minute:02d}"
                self.simulation_record.accumulate(
                    table_name="occupancy",
                    venue_type=venue_type,
                    occupancy=arr[:,0],
                    location_id=arr[:,1],
                    time=time,
                    #region_names=arr[:,2],
                    #super_area_names=arr[:,3],
                )
        self.simulation_record.time_step(self.timer.date)

        # Reset the counters for the next interval...
        self.initialise_occupancy_tracker()

    def process_results(self):
        """this is fast enough to process every time?"""
        self.read = RecordReader(
            self.simulation_outputs_path, 
            record_name="simulation_record.h5"
        )
        self.occupancy_df = self.read.table_to_df("occupancy", index="location_id")
        self.occupancy_df.reset_index(inplace=True)
        self.occupancy_df["timestamp"] = pd.to_datetime(self.occupancy_df["timestamp"])
        self.occupancy_df.set_index(
            ["venue_type", "timestamp", "time", "location_id"], inplace=True
        )
        self.occupancy_df.sort_index(inplace=True) # gets rid of lexsort error?
        occupancy_df_path = self.simulation_outputs_path / "occupancy.csv"
        self.occupancy_df.to_csv(occupancy_df_path)
        #self.locations_df = self.read.table_to_df("locations")
        #self.occupancy_df.merge() # can merge for by region.

    def load_results(self):
        #occupancy_df_path = self.simulation_outputs_path / "occupancy.csv"
        #self.occupancy_df = pd.read_csv(occupancy_df_path)      
        self.process_results()

    def plot_venue_occupancy(
        self, venue_type, timestamps=None, bins=None, color_palette=None,
    ):
        #if timestamps is None:
        #    timestamps = [dt.datetime(2020,2,28,10), dt.datetime(2020,2,29,8)]
        if color_palette is None:
            color_palette = {f"general_{i+1}": f"C{i}" for i in range(10)}
        f, ax = plt.subplots()
        #for timestamp in timestamps:
        #    date = timestamp.strftime("%Y-%m-%d")
        #    time = timestamp.strftime("%H:%M")
        total_data = self.occupancy_df.loc[venue_type]
        
        if bins is None:
            bins = np.linspace(0, total_data.values.max(), 25, endpoint=True, dtype=int)
            mids = 0.5*(bins[1:] + bins[:-1])
        for (timestamp, time), df in self.occupancy_df.groupby(["timestamp","time"]):
            if venue_type not in df.index:
                continue

            data = df.loc[venue_type]

            plot_kwargs = {}
            if timestamp.weekday() > 4:
                plot_kwargs["color"] = color_palette["general_1"]
            else:
                if time == "01:00":
                    plot_kwargs["color"] = color_palette["general_2"]
                elif time =="10:00":
                    plot_kwargs["color"] = color_palette["general_3"]
            
            hist,bin_edges = np.histogram(data,bins=bins)                     
            ax.plot(mids, hist, **plot_kwargs)
            ax.set_xlim(bins[0], bins[-1])
        ax.plot((0,0),(0,0), color=color_palette["general_1"], label="weekend timestep")
        ax.plot((0,0),(0,0), color=color_palette["general_2"], label="weekday 01:00-09:00")
        ax.plot((0,0),(0,0), color=color_palette["general_3"], label="weekday 10:00-13:00")
        ax.legend()
        return ax

    def plot_venue_occupancy_timeseries(
        self, venue_type, color_palette=None
    ):
        data = self.occupancy_df.loc[venue_type]

        timestamps = sorted(data.index.get_level_values(0).unique())
        weekend_timestamps = [t for t in timestamps if t.weekday() > 4]
        weekday_timestamps = [t for t in timestamps if t.weekday() <= 4]

        weekend_data = (
            data
            .loc[(weekend_timestamps, slice(None))]
            .groupby("timestamp")
            .agg({"occupancy": [np.mean, np.std]})
        )
        
        weekend_data.columns = ["_".join(col) for col in weekend_data.columns]
    
        weekday_data = (
            data
            .loc[(weekday_timestamps, slice(None))]
            .groupby(["timestamp", "time"])
            .agg({"occupancy": [np.mean, np.std]})
        )
        weekday_data.columns = ["_".join(col) for col in weekday_data.columns]

        drop_times = []
        for timestep in weekday_data.index.get_level_values(1).unique():
            if all(weekday_data.xs(timestep, level="time")["occupancy_mean"] == 0):
                print(venue_type, timestep)
                drop_times.append(timestep)
        weekday_data.drop(drop_times, level=1, axis=0, inplace=True)

        fig, ax = plt.subplots(figsize=(8,5))
        ax.scatter(
            weekend_data.index, weekend_data["occupancy_mean"], 
            color=color_palette["general_1"], s=5, label="weekend"
        )
        index_levels = weekday_data.index.get_level_values(1).unique()
        for ii, (weekday_time, weekday_time_data) in enumerate(weekday_data.groupby("time")):
            ax.scatter(
                weekday_time_data.index.get_level_values(0), weekday_time_data["occupancy_mean"],
                color=color_palette[f"general_{ii+2}"], label=f"weekday {weekday_time}", s=5
            )
        ax.legend()

        return ax

    def make_plots(self, save_dir, venue_types=None, color_palette=None):
        save_dir.mkdir(exist_ok=True, parents=True)
        if venue_types is None:
            venue_types = ["pub", "cinema", "grocery"]

        for venue_type in venue_types:
            venue_plot = self.plot_venue_occupancy(venue_type, color_palette=color_palette)
            venue_plot.plot()
            plt.savefig(save_dir / f"{venue_type}_occupancy.png", dpi=150, bbox_inches='tight')

            timeseries_plot = self.plot_venue_occupancy_timeseries(
                venue_type, color_palette=color_palette
            )
            timeseries_plot.plot()
            plt.savefig(save_dir / f"{venue_type}_occupancy_timeseries.png", dpi=150, bbox_inches='tight')
























