import psutil
import os
import pickle
import time
import datetime as dt
import json
import yaml
import argparse
import optparse
import logging
from itertools import combinations
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
numexpr_logger = logging.getLogger("numexpr.utils")
numexpr_logger.setLevel(logging.WARNING)

import matplotlib
matplotlib.use("Agg")

import h5py
import numpy as np
import numba as nb
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
import networkx as nx

from june.hdf5_savers import generate_world_from_hdf5
from june.groups.leisure import generate_leisure_for_config
#from june.groups.group import Group, Subgroup
from june.interaction import Interaction
#from june.interaction.interaction import _get_contacts_in_school
#from june.infection import HealthIndexGenerator
#from june.infection_seed import InfectionSeed, Observed2Cases
#from june.infection import InfectionSelector, HealthIndexGenerator
from june.groups.travel import Travel
from june.policy import Policies
from june.records import Record
#from june.demography import Person
from june import paths
from june.simulator import Simulator

from june.domain import Domain, DomainSplitter
from june.mpi_setup import mpi_rank, mpi_size, mpi_comm

from contact_simulator import ContactSimulator
from occupancy_simulator import OccupancySimulator
from time_spent_simulator import TimeSpentSimulator
from simulation_record import SimulationRecord, combine_hdf5s

#from leisure_simulator import LeisureSimulator

default_simulation_config_path = (
    paths.configs_path / "config_example.yaml"
)
default_interaction_path = (
    paths.configs_path / "defaults/interaction/interaction.yaml"
)

plt.style.use(['science'])
plt.style.reload_library()

logger = logging.getLogger(__file__)

plt_latex_logger = logging.getLogger("matplotlib.texmanager")
plt_latex_logger.setLevel(logging.WARNING)

default_color_palette = {
    'ONS': '#0c5da5',
    'JUNE': '#00b945',
    'general_1': '#ff9500',
    'general_2': '#ff2c00',
    'general_3': '#845b97',
    'general_4': '#474747',
    'general_5': '#9e9e9e',
    'male': 'orange',
    'female': 'maroon',
    '16_March': 'C2',
    '23_March': 'C3',
    '4_July': 'C1'
}

default_world_filename = 'world.hdf5'
default_output_plots_path = Path(__file__).absolute().parent.parent / "plots"
default_simulation_outputs_path = Path(__file__).absolute().parent / "simulation_outputs"

max_age = 100
bbc_bins = np.array([0,5,10,13,15,18,20,22,25,30,35,40,45,50,55,60,65,70,75,max_age])

def keys_to_int(x):
    return {int(k): v for k, v in x.items()}


def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit()
    def set_seed_numba(seed):
        random.seed(seed)
        np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return

def generate_domain(
    world_filename, 
    simulation_outputs_path=default_simulation_outputs_path
):
    """
    Given the current mpi rank, generates a split of the world (domain) from an hdf5 world.
    If mpi_size is 1 this will return the entire world.
    """
    save_path = Path(simulation_outputs_path)
    save_path.mkdir(exist_ok=True, parents=True)

    if mpi_rank == 0:
        with h5py.File(world_filename, "r") as f:
            super_area_names = [
                name.decode() for name in f["geography"]["super_area_name"]
            ]
            super_area_ids = [
                int(sa_id) for sa_id in f["geography"]["super_area_id"]
            ]
        super_area_name_to_id = {
            key: value for key, value in zip(super_area_names, super_area_ids)
        }
        # make dictionary super_area_id -> domain
        domain_splitter = DomainSplitter(
            number_of_domains=mpi_size, world_path=world_filename
        )
        super_areas_per_domain = domain_splitter.generate_domain_split(niter=60)
        super_area_names_to_domain_dict = {}
        super_area_ids_to_domain_dict = {}
        for domain, super_areas in super_areas_per_domain.items():
            for super_area in super_areas:
                super_area_names_to_domain_dict[super_area] = domain
                super_area_ids_to_domain_dict[
                    int(super_area_name_to_id[super_area])
                ] = domain

        with open(save_path / "super_area_ids_to_domain.json", "w") as f:
            json.dump(super_area_ids_to_domain_dict, f)
        with open(save_path / "super_area_names_to_domain.json", "w") as f:
            json.dump(super_area_names_to_domain_dict, f)
    mpi_comm.Barrier() # wait until rank 0 writes domain partition
    if mpi_rank > 0:
        with open(save_path / "super_area_ids_to_domain.json", "r") as f:
            super_area_ids_to_domain_dict= json.load(f, object_hook=keys_to_int)
    domain = Domain.from_hdf5(
        domain_id=mpi_rank,
        super_areas_to_domain_dict=super_area_ids_to_domain_dict,
        hdf5_file_path=world_filename,
    )
    return domain

class SimulationPlotter:

    def __init__(
        self,
        world,
        world_name=None,
        contact_counter=False,
        contact_tracker=False,
        occupancy_tracker=False,
        time_spent_tracker=False,
        simulation_outputs_path=default_simulation_outputs_path,
    ):
        self.world = world
        self.world_name = world_name
        self.contact_counter = contact_counter
        self.contact_tracker = contact_tracker
        self.occupancy_tracker = occupancy_tracker
        self.time_spent_tracker = time_spent_tracker

        self.simulation_outputs_path = Path(simulation_outputs_path)
        # this bit is veeery broken in mpi. stick with overwriting for now...
        """simulation_outputs_path = Path(simulation_outputs_path)
        ii=1
        while self.simulation_outputs_path.exists():
            self.simulation_outputs_path = (
                simulation_outputs_path.parent / f"{simulation_outputs_path.stem}_{ii}"
            )
            ii+=1"""
        self.simulation_outputs_path.mkdir(exist_ok=True, parents=True)

    @classmethod
    def from_file(
        cls,
        world_filename: str = default_world_filename,
        simulation_outputs_path=default_simulation_outputs_path,         
        operation_args={}
    ):
        if mpi_size == 1:
            world = generate_world_from_hdf5(world_filename)
        else:
            world = generate_domain(
                world_filename, simulation_outputs_path=simulation_outputs_path
            )
        print(f"world {mpi_rank} has {len(world.people)} people")
        return SimulationPlotter(
            world, 
            world_name=Path(world_filename).stem,
            simulation_outputs_path=simulation_outputs_path,
            **operation_args
        )

    @classmethod
    def without_world(
        cls, simulation_outputs_path=default_simulation_outputs_path, operation_args={}
    ):
        simulation_plotter = SimulationPlotter(
            None,
            simulation_outputs_path=simulation_outputs_path,
            **operation_args
        )
        simulation_plotter.simulator = None
        return simulation_plotter
  
    def generate_simulator(
        self,
        simulation_config_path=default_simulation_config_path,
    ):
        "Set up the simulator"
        interaction = Interaction.from_file(
            population=self.world.people
        )
        travel = Travel()
        policies = Policies.from_file()
        leisure = generate_leisure_for_config(
            self.world,
        )
        self.simulator = Simulator.from_file(
            world=self.world,
            interaction=interaction,
            config_filename=simulation_config_path,
            leisure=leisure,
            travel=travel,
            infection_seed=None, #infection_seed,
            infection_selector=None, #infection_selector,
            policies=policies,
            record=Record,
        )

        # world doesn't normall have attr supergroups.
        self.world.supergroups = [
            self.world.care_homes,
            self.world.cinemas, 
            self.world.city_transports, 
            self.world.inter_city_transports, 
            self.world.companies, 
            self.world.groceries, 
            self.world.hospitals, 
            self.world.households, 
            self.world.pubs, 
            self.world.schools, 
            self.world.universities
        ]

    def load_operations(
        self, 
        simulation_days=7,
        generate_simulation_record=True,
    ):
        "Loads classes with functions to be called during the simuation timesteps"

        #if contact_tracker_pickle_path is None:
        if generate_simulation_record:
            simulation_record = SimulationRecord(
                self.simulation_outputs_path, 
                contact_counter=self.contact_counter, 
                contact_tracker=self.contact_tracker,
                occupancy_tracker=self.occupancy_tracker,
                mpi_rank=mpi_rank,
                record_static_data=True,
            )
            simulation_record.static_data(world=self.world)
        else:
            simulation_record=None
        if self.contact_counter or self.contact_tracker:
            self.contact_simulator = ContactSimulator(
                simulator=self.simulator,
                simulation_record=simulation_record,
                contact_tracker=self.contact_tracker,
                simulation_outputs_path=self.simulation_outputs_path,
                age_bins={"bbc": bbc_bins, "five_yr": np.arange(0,105,5)},
                simulation_days=simulation_days,
                world_name=self.world_name  
            )
        else:
            self.contact_simulator = None
        if self.occupancy_tracker:
            self.occupancy_simulator = OccupancySimulator(
                simulator=self.simulator,
                simulation_record=simulation_record,
                simulation_outputs_path=self.simulation_outputs_path,
                simulation_days=simulation_days
            )
        else:
            self.occupancy_simulator = None
        if self.time_spent_tracker:
            self.time_spent_simulator = TimeSpentSimulator(  
                simulator=self.simulator,
                simulation_record=simulation_record,
                simulation_outputs_path=self.simulation_outputs_path,
                simulation_days=simulation_days
            )
        else:
            self.time_spent_simulator = None
    
    def advance_step(self):
        "Advance a simulation time step and carry out operations"
        self.simulator.clear_world()
        delta_t = self.simulator.timer.delta_time.seconds / 3600.
        (
            people_from_abroad_dict,
            n_people_from_abroad,
            n_people_going_abroad,
            people_to_send_abroad
        ) = self.simulator.activity_manager.do_timestep(return_to_send_abroad=True)
        self.operations(people_from_abroad_dict, people_to_send_abroad)
        next(self.simulator.timer)

    def operations(self, people_from_abroad_dict, to_send_abroad):  
        tick = time.time()               

        if self.contact_simulator is not None:
            self.contact_simulator.global_operations(to_send_abroad)
        if self.occupancy_simulator is not None:
            self.occupancy_simulator.global_operations() # this is really just "pass"
        if self.time_spent_simulator is not None:
            self.time_spent_simulator.global_operations()

        for supergroup in self.world.supergroups: # world does not 
            if len(supergroup) == 0:
                continue
            spec = supergroup[0].spec
            for group in supergroup:
                if group.external:
                    continue
                people_from_abroad = people_from_abroad_dict.get(
                    group.spec, {}
                ).get(group.id, None)                    
                interactive_group = group.get_interactive_group(people_from_abroad)
                self.modify_interactive_group(interactive_group, people_from_abroad)
                if self.contact_simulator is not None:
                    self.contact_simulator.group_operations(interactive_group)
                if self.occupancy_simulator is not None:
                    self.occupancy_simulator.group_operations(interactive_group)
                if self.time_spent_simulator is not None:
                    self.time_spent_simulator.group_operations(interactive_group)
        
        # record outputs at certain steps.
        if self.contact_simulator is not None:
            self.contact_simulator.concluding_operations()
            if self.simulator.timer.date in self.save_points:
                self.contact_simulator.record_output()
        if self.occupancy_simulator is not None:
            self.occupancy_simulator.record_output()
        if self.time_spent_simulator is not None:
            if self.simulator.timer.date == self.end_time:
                self.time_spent_simulator.record_output()
        tock = time.time()
        print(f"{mpi_rank} {self.simulator.timer.date} done in {(tock-tick)/60.} min")

    def modify_interactive_group(self, interactive_group, people_from_abroad):
        """"""
        people_from_abroad = people_from_abroad or {}

        interactive_group.subgroup_member_ids = []
        for subgroup_index, subgroup in enumerate(interactive_group.group.subgroups):
            subgroup_size = len(subgroup.people)
            if subgroup.subgroup_type in people_from_abroad:
                people_abroad_data = people_from_abroad[subgroup.subgroup_type]
                people_abroad_ids = people_abroad_data.keys()
                subgroup_size += len(people_abroad_ids)
            else:
                people_abroad_data = None
                people_abroad_ids = []
             
            this_subgroup_ids = [p.id for p in subgroup.people] + list(people_abroad_ids)
            interactive_group.subgroup_member_ids.append(this_subgroup_ids)

        if interactive_group.group.spec == "school":
            if (len(interactive_group.subgroup_member_ids) == 
                len(interactive_group.school_years) + 2):
                assert len(interactive_group.subgroup_member_ids[-1]) == 0
                del interactive_group.subgroup_member_ids[-1]
            else:
                print("you can probably remove this 'if school' statement in modify_interactive_group")
        
    def run_simulation(
        self,
        simulation_days = 7,
        save_interval = 7,
        save_all = True
    ):
        "Run simulation with pre-built simualtor"
        
        self.start_time = self.simulator.timer.date
        self.end_time = self.start_time + dt.timedelta(days=simulation_days)
        
        self.save_points = [ 
            self.simulator.timer.date + dt.timedelta(days=n*save_interval) 
            for n in range(1,simulation_days//save_interval+1)
        ]
        if self.save_points[-1] != self.end_time:
            self.save_points.append(self.end_time)
        
        ### THE MAIN EVENT ###
        while self.simulator.timer.date <= self.end_time:
            self.advance_step()
        ### ============== ###

        if save_all:
            if self.contact_counter or self.contact_tracker:
                self.contact_simulator.save_auxilliary_data()
        mpi_comm.Barrier() # Wait for all the cores to catch up.

        if mpi_rank == 0:
            combine_hdf5s(record_path=self.simulation_outputs_path)
            if self.contact_counter or self.contact_tracker:
                self.contact_simulator.process_results()
            if self.occupancy_tracker:
                self.occupancy_simulator.process_results()
            if self.time_spent_tracker:
                self.time_spent_simulator.process_results()

    def make_plots(self):
        """Call class functions to create plots"""
        if self.contact_counter or self.contact_tracker:
            self.contact_simulator.load_results()
            self.contact_simulator.make_plots(                
                save_dir=self.simulation_outputs_path / "contact_tracker",
                color_palette=default_color_palette
            )
        if self.occupancy_tracker:
            self.occupancy_simulator.load_results()
            self.occupancy_simulator.make_plots(
                save_dir=self.simulation_outputs_path / "occupancy",
                color_palette=default_color_palette
            )
        if self.time_spent_tracker:
            self.time_spent_simulator.load_results()
            self.time_spent_simulator.make_plots(
                save_dir=self.simulation_outputs_path / "time_spent",
                color_palette=default_color_palette
            )

    def run_all(self, simulation_days=7, make_plots = True):
        """
        Run everything
        Note: What is called here is all that should need to be called
        """
        
        self.generate_simulator()
        self.load_operations(
            simulation_days=simulation_days,
        )        
        self.run_simulation(simulation_days=simulation_days)
        if mpi_rank == 0:
            if make_plots:
                self.make_plots()
        

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Plotter for mini-simulations.", 
        formatter_class=argparse.RawTextHelpFormatter
    )

    ## try to keep these lower case.
    parser.add_argument(
        "-w",
        "--world_filename",
        help="Relative directory to world file",
        required=False,
        default=default_world_filename
    )
    parser.add_argument(
        "-c",
        "--simulation_config",
        help="Relative directory to simulation config",
        required=False,
        default=default_simulation_config_path
    )
    parser.add_argument(
        "-o",
        "--outputs_dir",
        help="Directory to store records, etc.",
        required=False,
        default=default_simulation_outputs_path
    )
    parser.add_argument(
        "-p",
        "--only_plots",
        help="don't load the world; only make plots",
        action="store_true",
        required=False,
        default=False,
    )
    parser.add_argument(
        "-d",
        "--simulation_days",
        help="how many days to run the simulation for",
        type=int,
        required=False,
        default=7,
    )

    ## set up the operations switches, try to keep uppercase.
    operations_dict = {
        "C": "contact_counter", 
        "T": "contact_tracker", 
        "O": "occupancy_tracker",
        #"D": "distance_tracker",
        "S": "time_spent_tracker",
    }
    operations_notes = {"T":"(warning: *VERY* large output)", "D":"(coming soon...)"}
    padding = "\n    "
    operations_str = padding.join(
        f"{k}: {v} {operations_notes.get(k,'')}" for k, v in operations_dict.items()
    )
    operations_help = (
        "choose which operations to switch on\ndefault is contact_counter, occupancy;"
        + "\n    equivalent to '--operations CO'"
        + "\nchoose any number from:"
        + f"{padding}{operations_str}"
    )
    parser.add_argument(
        "--operations","--ops",
        help=operations_help,
        required=False,
        default="CO",
    )
        
    args = parser.parse_args()
    args.outputs_dir = Path.cwd() / args.outputs_dir

    if mpi_rank == 0:
        logger.info(f"saving outputs to {args.outputs_dir}")

    operation_args = {}
    for op in args.operations:
        if op not in operations_dict:
            raise ValueError(f"{op} not a recognised argument. Choose from {operations_dict}")
        operation_args[operations_dict[op]] = True

    start_time = time.time()

    if not args.only_plots:
        simulation_plotter = SimulationPlotter.from_file(
            args.world_filename, 
            simulation_outputs_path=args.outputs_dir,
            operation_args=operation_args
        )
        simulation_plotter.generate_simulator()
        simulation_plotter.run_all(simulation_days=args.simulation_days)
    else:
        simulation_plotter = SimulationPlotter.without_world(
            simulation_outputs_path=args.outputs_dir,
            operation_args=operation_args
        )
        simulation_plotter.load_operations(generate_simulation_record=False)
        if mpi_rank == 0:
            simulation_plotter.make_plots()

    end_time = time.time()
    mins = (end_time-start_time) / 60.

    if mpi_rank == 0:
        logger.info(f"main loop done in {mins:.3f} mins")




