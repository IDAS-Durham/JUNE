import psutil
import os
import pickle
import time
import datetime as dt
import yaml
from itertools import combinations
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
import tables
import networkx as nx
#import seaborn as sns

from june.demography import Person
from june.groups.leisure import generate_leisure_for_config
from june.groups.group import Group, Subgroup
from june.groups.travel import Travel
from june.hdf5_savers import generate_world_from_hdf5
from june.infection import HealthIndexGenerator
from june.infection import InfectionSelector, HealthIndexGenerator
from june.infection_seed import InfectionSeed, Observed2Cases
from june.interaction import Interaction
from june.interaction.interaction import _get_contacts_in_school
from june.policy import Policies
from june.records import Record, RecordReader
from june.records.event_records_writer import EventRecord
from june.records.static_records_writer import (
    PeopleRecord,
    LocationRecord,
    AreaRecord,
    SuperAreaRecord,
    RegionRecord,
)
from june.simulator import Simulator

from june import paths




default_simulation_config_path = (
    paths.configs_path / "config_example.yaml"
)
default_interaction_path = (
    paths.configs_path / "defaults/interaction/interaction.yaml"
)
default_contact_data_paths = {
    "bbc": paths.data_path / "plotting/contact_tracking/BBC.csv",
    "polymod": paths.data_path / "plotting/contact_tracking/polymod.csv",
}

class SimulationRecord:
    """
    A special record class to record data specific to the simulation_plotter functions.
    """

    def __init__(
        self, record_path: str,
        contact_tracker=False,
        contact_counter=False,
        occupancy_tracker=False,
        mpi_rank=None,
        record_static_data=False,
    ):
        self.record_path = Path(record_path)
        self.record_path.mkdir(parents=True, exist_ok=True)
        self.mpi_rank = mpi_rank
        if mpi_rank is not None:
            self.filename = f"simulation_record.{mpi_rank:03d}.h5"
            self.summary_filename = f"simulation_summary.{mpi_rank:03d}.csv"
        else:
            self.filename = f"simulation_record.h5"
            self.summary_filename = f"simulation_summary.csv"
        self.configs_filename = f"config.yaml"
        try:
            os.remove(self.record_path / self.filename)
        except OSError:
            pass
        with tables.open_file(self.record_path / self.filename, mode="w") as self.file:
            self.output_tables = {
                "counter": CounterRecord(hdf5_file=self.file),
                "tracker": TrackerRecord(hdf5_file=self.file),
                "occupancy": OccupancyRecord(hdf5_file=self.file),
            }
            if record_static_data:
                self.statics = {
                    "people": PeopleRecord(hdf5_file=self.file),
                    "locations": LocationRecord(hdf5_file=self.file),
                    #"areas": AreaRecord(hdf5_file=self.file),
                    #"super_areas": SuperAreaRecord(hdf5_file=self.file),
                    #"regions": RegionRecord(hdf5_file=self.file),
                }

    def static_data(self, world: "World"):
        with tables.open_file(self.record_path / self.filename, mode="a") as self.file:
            for static_name in self.statics.keys():
                self.statics[static_name].record(hdf5_file=self.file, world=world)

    def accumulate(self, table_name: str, **kwargs):
        self.output_tables[table_name].accumulate(**kwargs)

    def time_step(self, timestamp: str, outputs_to_record=None):
        if outputs_to_record is None:
            outputs_to_record = [x for x in self.output_tables.keys()]
        with tables.open_file(self.record_path / self.filename, mode="a") as self.file:
            for output in outputs_to_record:
                self.output_tables[output].record(hdf5_file=self.file, timestamp=timestamp)

class CounterRecord(EventRecord):
    """Track just number of contacts"""
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="counter",
            int_names=["id"],
            float_names=["num_contacts"],
            str_names=["contact_type",],
        )

    def accumulate(
        self, contact_type, person_ids, num_contacts, #region_name, 
    ):
        self.contact_type.extend([contact_type] * len(person_ids))
        #self.location_ids.extend([location_id] * len(person_ids))
        #self.region_names.extend([region_name] * len(person_ids))
        self.id.extend(person_ids)
        self.num_contacts.extend(num_contacts)

class TrackerRecord(EventRecord):
    """track specific ids of contacts"""
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="tracker",
            int_names=["id", "contact_ids", "tracker_count"], #,"location_ids"]
            float_names=[],
            str_names=["contact_type"] #, "region_names"],
        )

    def accumulate(
        self, contact_type, person_ids, contact_ids, tracker_count#region_name, 
    ):
        self.contact_type.extend([contact_type] * len(contact_ids))
        #self.location_ids.extend([location_id] * len(contact_ids))
        #self.region_names.extend([region_name] * len(contact_ids))
        self.id.extend(person_ids)
        self.contact_ids.extend(contact_ids)
        self.tracker_count.extend(tracker_count)
                
class OccupancyRecord(EventRecord):
    """track specific ids of contacts"""
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="occupancy",
            int_names=["location_id", "occupancy"],
            float_names=[],
            str_names=["venue_type", "time"],
        )

    def accumulate(
        self, venue_type, occupancy, location_id, time
    ):
        self.venue_type.extend([venue_type] * len(occupancy))
        self.occupancy.extend(occupancy)
        self.location_id.extend(location_id)
        self.time.extend([time] * len(occupancy))
        #self.region_names.extend(region_names)
        #self.super_area_names.extend(super_area_names)

def combine_hdf5s(
    record_path,
    table_names=("counter", "tracker", "occupancy"),
    remove_left_overs=False,
    save_dir=None,
):
    record_files = record_path.glob("simulation_record.*.h5")
    if save_dir is None:
        save_path = Path(record_path)
    else:
        save_path = Path(save_dir)
    full_record_save_path = save_path / "simulation_record.h5"
    with tables.open_file(full_record_save_path, "w") as merged_record:
        for i, record_file in enumerate(record_files):
            print(f"record {i}")
            with tables.open_file(str(record_file), "r") as record:
                datasets = record.root._f_list_nodes()
                for dataset in datasets:
                    arr_data = dataset[:]
                    if i == 0:
                        description = getattr(record.root, dataset.name).description
                        merged_record.create_table(
                            merged_record.root, dataset.name, description=description,
                        )
                    if len(arr_data) > 0:
                        table = getattr(merged_record.root, dataset.name)
                        table.append(arr_data)
                        table.flush()
            if remove_left_overs:
                record_file.unlink()




