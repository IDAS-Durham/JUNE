import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
from june.collections import defaultdict
import argparse
import os
import mpu
import matplotlib.pyplot as plt

from june import paths

default_size_nr_file = (
    paths.data_path / "input/households/household_size_per_area.csv"
)

class HouseholdPlots:

    def __init__(self, world):
        self.world = world

    def load_household_data(
            self,
            household_size_per_area_filename= default_size_nr_file,
    ):
        "Loading household data for plotting"

        self.household_sizes_per_area_data = pd.read_csv(household_size_per_area_filename)
        self.household_sizes_per_area_data.set_index("geography", inplace=True)

    def plot_household_sizes(self):
        "Plotting the size of households"

        JUNE_household_sizes = defaultdict(int)
        for household in self.world.households:
            JUNE_household_sizes[household.n_residents] += 1

        

        f, ax = plt.subplots()
        ax.bar(size_brackets[:-1], world_household_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='NOMIS sizes')
        ax.bar(size_brackets[:-1], JUNE_household_sizes_binned, width=bin_widths, align='edge', alpha=0.7, label='JUNE sizes')
        ax.set_xlim((-5,np.max(size_brackets)))
        ax.set_yscale('log')
        ax.set_ylabel('Frequency')
        ax.set_xlabel('Number of people')
        ax.legend()

        return ax

