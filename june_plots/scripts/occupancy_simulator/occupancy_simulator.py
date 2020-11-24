import psutil
import os
import copy
import pickle
import time
import datetime as dt
import yaml
from collections import Counter, defaultdict, ChainMap
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
import tables
import networkx as nx
#import seaborn as sns

#from june_runs import Runner

#default_run_config_path = (
#    "/home/aidan/covid/june_runs/example_run/runs/run_000/parameters.json"#"/home/aidan/covid/june_runs/configuration/run_sets/quick_examples/local_example.yaml"
#)

from june.hdf5_savers import generate_world_from_hdf5
from june.groups.leisure import generate_leisure_for_config, SocialVenue
from june.groups.group import Group, Subgroup
from june.interaction import Interaction, InteractiveGroup
from june.interaction.interaction import _get_contacts_in_school
from june.infection import HealthIndexGenerator
from june.infection_seed import InfectionSeed, Observed2Cases
from june.infection import InfectionSelector, HealthIndexGenerator
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
            self.group_types = [
                #self.world.care_homes,
                self.world.cinemas, 
                #self.world.city_transports, 
                #self.world.inter_city_transports, 
                #self.world.companies, 
                self.world.groceries, 
                #self.world.hospitals, 
                #self.world.households, # households aren't really all that interesting?
                self.world.pubs, 
                #self.world.schools, 
                #self.world.universities
            ]
            self.initialise_occupancy_tracker()

    def initialise_occupancy_tracker(self):
        self.occupancy_tracker = (
            {groups[0].spec: [] for groups in self.group_types if len(groups) > 0}
        )

    def track_occupancy(self, n_people, group: Group):
        if isinstance(group, SocialVenue):
            occ = n_people #/ group.max_size
        self.occupancy_tracker[group.spec].append(
            (occ, group.id) #, group.super_area.region, group.super_area)
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

    def operations(
        self, people_from_abroad_dict, to_send_abroad, record_time_step=False):
        """The main thing in this simulator."""
        for group_type in self.group_types:
            if len(group_type) == 0:
                continue
            group_spec = group_type[0].spec
            for group in group_type:
                if group.external:
                    continue
                if (
                    group.spec in people_from_abroad_dict
                    and group.id in people_from_abroad_dict[group.spec]
                ):
                    foreign_people = people_from_abroad_dict[group.spec][group.id]
                else:
                    foreign_people = None
                int_group = InteractiveGroup(
                    group, foreign_people, save_subgroup_ids=True
                )
                if int_group.size == 0:
                    continue                
                self.track_occupancy(int_group.size, group)
        self.record_output()

    def process_results(self):
        pass

    def load_results(self):
        """this is fast enough to process every time?"""
        self.read = RecordReader(
            self.simulation_outputs_path, 
            record_name="simulation_record.h5"
        )
        self.occupancy_df = self.read.table_to_df("occupancy", index="location_id")
        self.occupancy_df.reset_index(inplace=True)
        self.occupancy_df["timestamp"] = pd.to_datetime(self.occupancy_df["timestamp"])
        self.occupancy_df.set_index(["venue_type", "timestamp", "time"], inplace=True)

        self.occupancy_df.sort_index(inplace=True) # gets rid of lexsort error?
        #self.locations_df = self.read.table_to_df("locations")
        #self.occupancy_df.merge() # can merge for by region.

    def plot_venue_occupancy(
        self, venue_type, timestamps=None, bins=None, color_palette=None,
    ):
        #if timestamps is None:
        #    timestamps = [dt.datetime(2020,2,28,10), dt.datetime(2020,2,29,8)]
        if bins is None:
            dx = 0.05
            bins = np.arange(0., 1. + dx, dx)
        if color_palette is None:
            color_palette = {"general_1": "C0", "general_2": "C1", "general_3": "C2"}

        mids = 0.5*(bins[1:]+bins[:-1])
        f, ax = plt.subplots()
        #for timestamp in timestamps:
        #    date = timestamp.strftime("%Y-%m-%d")
        #    time = timestamp.strftime("%H:%M")
        for (timestamp, time), df in self.occupancy_df.groupby(["timestamp","time"]):
            data = df.loc[venue_type]
            #    (venue_type, date, time)
            #]
            print(data)
            plot_kwargs = {}
            if timestamp.weekday() > 4:
                plot_kwargs["color"] = color_palette["general_1"]
            else:
                if time == "01:00":
                    plot_kwargs["color"] = color_palette["general_2"]
                elif time =="10:00":
                    plot_kwargs["color"] = color_palette["general_3"]
            
            hist,_ = np.histogram(data,bins=bins)
            ax.plot(mids, hist, **plot_kwargs)
            ax.set_xlim(0.0,1.0)
        ax.plot((0,0),(0,0), color=color_palette["general_1"], label="weekend timestep")
        ax.plot((0,0),(0,0), color=color_palette["general_2"], label="weekday 01:00-09:00")
        ax.plot((0,0),(0,0), color=color_palette["general_3"], label="weekday 10:00-13:00")
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

























