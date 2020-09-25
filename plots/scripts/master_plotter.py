import numpy as np
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from policy import PolicyPlots

default_save_dir = ''

class Plotting:

    def __init__(
            self,
            world = default_world,
            save_dir = default_save_dir,
    ):

        self.world = world

    @classmethod
    def from_file(
            cls,
            world_filename: str = default_world_filename,
    ):
        [LOAD WORLD]

        return Plotting(world)
        
    def plot_policies(self):

        policy_plots = PolicyPlots(self.world)

        school_reopening_plot = policy_plots.plot_school_reopening()

        school_reopening_plot.savefig()
        

    
