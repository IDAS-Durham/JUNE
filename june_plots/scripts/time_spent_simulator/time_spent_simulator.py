from collections import Counter, defaultdict
import logging

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

logger = logging.getLogger(__name__)

class TimeSpentSimulator:
    
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
                self.world.care_homes,
                self.world.cinemas, 
                self.world.city_transports, 
                self.world.inter_city_transports, 
                self.world.companies, 
                self.world.groceries, 
                self.world.hospitals, 
                self.world.households, # households aren't really all that interesting?
                self.world.pubs, 
                self.world.schools, 
                self.world.universities
            ]
            self.contact_types = (
                [groups[0].spec for groups in self.group_types if len(groups) > 0]
                + ["care_home_visits", "household_visits"]
            )
            self.initialise_time_spent_tracker()

    def initialise_time_spent_tracker(self):
        self.time_spent_tracker = {spec: defaultdict(float) for spec in self.contact_types}

    def track_time_spent(self, delta_t, group: InteractiveGroup, household_visit=False):
        if household_visit:
            venue_type = f"household_visits"
        else:
            venue_type = group.spec
        for subgroup_type, subgroup_ids in enumerate(group.subgroup_member_ids):
            if group.spec == "care_home" and subgroup_type == 2: # sg_type 2 is visitors...
                venue_type == "care_home_visits"
                # shouldn't need to reset this as visitors should always be the last group.
            for pid in subgroup_ids:
                self.time_spent_tracker[venue_type][pid] += delta_t

    def record_output(self):
        if mpi_rank == 0:
            logger.info(f"recording output at {self.timer.date}")
        for venue_type in self.time_spent_tracker.keys():
            if len(self.time_spent_tracker[venue_type]) > 0: # ie. no one in pub in sleep timestep.
                person_ids = list(self.time_spent_tracker[venue_type].keys())
                time_spent = list(self.time_spent_tracker[venue_type].values())
                self.simulation_record.accumulate(
                    table_name="time_spent",
                    venue_type=venue_type,
                    person_ids=person_ids,
                    time_spent=time_spent,
                )
        self.simulation_record.time_step(self.timer.date)

        # Reset the counters for the next interval...
        self.initialise_time_spent_tracker()

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
                household_visit = False
                if group.spec == "household":
                    for person in group.people:
                        if person.leisure is not None and person.leisure.group.id == person.residence.group.id:
                            household_visit = True
                if int_group.size == 0:
                    continue

                delta_t = self.timer.delta_time.seconds / 3600.
                self.track_time_spent(delta_t, int_group, household_visit=household_visit)
        if record_time_step:
            self.record_output()

    def process_results(self, combined_venues=None):
        if combined_venues is None:
            combined_venues = {
            "visits": ["household_visits"], 
            "total_leisure": ["pub", "grocery", "cinema", "visits"]
        }
        print("processing results!")
        self.read = RecordReader(
            self.simulation_outputs_path, 
            record_name="simulation_record.h5"
        )
        population = self.read.table_to_df("population", index="id")
        drop_cols = [
            "primary_activity_id", 
            "residence_id", 
            "residence_type",
            "area_id", 
            "primary_activity_type",
            "socioeconomic_index", "ethnicity"
        ]
        population.drop(drop_cols, axis=1, inplace=True)
        time_spent = self.read.table_to_df("time_spent", index="id")
        #time_spent = pd.merge(
        #    time_spent, population, how="inner", left_index=True, right_index=True, validate="many_to_one"
        #)
        #self.time_spent.drop(drop_cols, axis=1, inplace=True)
        pd.set_option('display.max_columns', 20)
        print(time_spent)
        time_spent.reset_index(inplace=True)
        unique_venue_types = list(time_spent["venue_type"].unique())
        time_spent.set_index(["id","venue_type"], inplace=True)
        print(time_spent)
        
        ### !!!=============NOTE HERE!=============!!! ###
        # Need to do this step as some people have time recorded in two/three domains,
        # so each person
        time_spent = time_spent.groupby(level=[0,1]).agg(
            {"time_spent": sum}
        )
        unstack = time_spent["time_spent"].unstack(level=1,fill_value=0.)
        print(len(population), len(unstack))
        time_spent = pd.merge(
            unstack, population, how="inner", left_index=True, right_index=True, validate="one_to_one"
        )
        time_spent.drop(["sex"], axis=1, inplace=True)
        for k, l in combined_venues.items():
            time_spent[k] = time_spent[l].sum(axis=1)
        agg_dict = {k: [np.mean, np.std] for k in unique_venue_types+list(combined_venues.keys())}
        self.time_spent = time_spent.groupby("age").agg(agg_dict)
        self.time_spent.columns = [
            f"{col[0]}" if col[1] == "mean" else "_".join(col) for col in self.time_spent.columns
        ]
        average_time_spent_path = self.simulation_outputs_path / "average_time_spent.csv"
        self.time_spent.to_csv(average_time_spent_path, index=True)
        
    def load_results(self):
        average_time_spent_path = self.simulation_outputs_path / "average_time_spent.csv"
        self.time_spent = pd.read_csv(average_time_spent_path, index_col=0)

    def plot_time_spent(
        self, venue_types, std=False, color_palette=None,
    ):
        if color_palette is None:
            color_palette = {f"general_{i+1}":"C{i}" for i in range(10)}
        
        f, ax = plt.subplots()
        if type(venue_types) is str:
            venue_types = [venue_types]
        for i, venue_type in enumerate(venue_types):
            data = self.time_spent[venue_type]
            label = venue_type.replace("_", " ") # stupid latex error...
            if std:
                std_data = self.time_spent[f"{venue_type}_std"]
                ax.fill_between(
                    self.time_spent.index, np.maximum(0, data-std_data), data+std_data, 
                    color=color_palette[f"general_{i+1}"], alpha=0.5
                )
            ax.plot(
                self.time_spent.index, data, 
                color=color_palette[f"general_{i+1}"], label=label
            )
        ax.legend()
        return ax

    def make_plots(
        self, save_dir, std=False, venue_types: dict=None, color_palette: dict=None
    ):
        save_dir.mkdir(exist_ok=True, parents=True)
        if venue_types is None:
            venue_types = {
                "leisure": ["pub", "cinema", "grocery", "visits", "total_leisure"],
                "primary_activity": ["care_home", "school", "company", "university"]
            }

        for name, venue_type_list in venue_types.items():
            print(venue_type_list)
            venue_plot = self.plot_time_spent(
                venue_type_list, std=std, color_palette=color_palette
            )
            venue_plot.plot()
            plt.savefig(save_dir / f"{name}_time.png", dpi=150, bbox_inches='tight')




