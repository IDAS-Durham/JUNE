import psutil
import os
import pickle
import time
import datetime as dt
import yaml
import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
import networkx as nx

from june.hdf5_savers import generate_world_from_hdf5
from june.groups.leisure import generate_leisure_for_config
from june.groups.group import Group, Subgroup
from june.interaction import Interaction
from june.interaction.interaction import _get_contacts_in_school
from june.infection import HealthIndexGenerator
from june.infection_seed import InfectionSeed, Observed2Cases
from june.infection import InfectionSelector, HealthIndexGenerator
from june.groups.travel import Travel
from june.policy import Policies
from june.records import Record
from june.demography import Person
from june import paths
from june.simulator import Simulator

from contact_tracker import ContactTracker
#from leisure_simulator import LeisureSimulator

default_simulation_config_path = (
    paths.configs_path / "config_example.yaml"
)
default_interaction_path = (
    paths.configs_path / "defaults/interaction/interaction.yaml"
)

plt.style.use(['science'])
plt.style.reload_library()

colors = {
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

max_age = 100
bbc_bins = np.array([0,5,10,13,15,18,20,22,25,30,35,40,45,50,55,60,65,70,75,max_age])

class SimulationPlotter:

    def __init__(
            self,
            world
    ):
        self.world = world

    @classmethod
    def from_file(
            cls,
            world_filename: str = default_world_filename,
    ):
        world = generate_world_from_hdf5(world_filename)

        return SimulationPlotter(world)
  
    def generate_simulator(
            self,
            simulation_config_path=default_simulation_config_path
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

    def load_operations(self, contact_tracker_pickle=None):
        "Loads classes with functions to be called during the simuation timesteps"

        if contact_tracker_pickle is None:
            self.contact_simulator = ContactTracker(
                self.simulator.world,
                age_bins={"bbc":bbc_bins, "five_yr": np.arange(0,105,5)}
                
            )
            self.do_tracker=True
        else:
            self.contact_simulator = ContactTracker.from_pickle(
                self.simulator.world,
                contact_tracker_pickle=contact_tracker_pickle
            )
            self.do_tracker=False
        #self.leisure_simulator = LeisureSimulator([args])

    def advance_step(self):
        "Advance a simulation time step and carry out operations"
        
        print(self.simulator.timer.date)
        self.simulator.clear_world()
        delta_t = self.simulator.timer.delta_time.seconds / 3600.

        self.simulator.activity_manager.do_timestep()

        # carry out timestep operations
        if self.do_tracker: # No need to tracker counting if reading prev. sim. from pickle...
            self.contact_simulator.operations()
        #self.leisure_simulator_operations() # this should be a function in the LeisureSimulator class

        next(self.simulator.timer)
        
        
    def run_simulation(
            self,
            simulation_days = 7,
            save_all = True
    ):
        "Run simulation with pre-built simualtor"
        
        start_time = self.simulator.timer.date
        end_time = start_time + dt.timedelta(days=simulation_days)

        while self.simulator.timer.date < end_time:
            self.advance_step()

        if save_all:
            self.contact_simulator.save_tracker()
            #### SAVE OUT OTHERS HERE ####

        self.contact_simulator.process_contacts()

    def make_plots(self):
        "Call class functions to create plots"
        
        self.contact_tracker.make_plots(
            save_dir = default_output_plots_path / "contact_tracker"
        )
        ### CALL class functions which make plots ###

    def run_all(self, make_plots = True):
        """
        Run everything
        Note: What is called here is all that should need to be called
        """
        
        self.generate_simulator()
        self.load_operations()        
        self.run_simulation()
        if make_plots:
            self.make_plots()
        
            

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Plotter for JUNE's world.")

    parser.add_argument(
        "-w",
        "--world_filename",
        help="Relative directory to world file",
        required=False,
        default = default_world_filename
    )

    args = parser.parse_args()
    simulation_plotter = SimulationPlotter.from_file(args.world_filename)

    simulation_plotter.run_all()
