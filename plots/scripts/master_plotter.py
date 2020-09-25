import numpy as np
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from june.hdf5_savers import generate_world_from_hdf5
from policy import PolicyPlots

plt.style.use(['science'])
plt.style.reload_library()

default_world_filename = 'world.hdf5'

class Plotting:

    def __init__(
            self,
            world = default_world,
    ):

        self.world = world

    @classmethod
    def from_file(
            cls,
            world_filename: str = default_world_filename,
    ):
        world = generate_world_from_hdf5(world_filename)

        return Plotting(world)
        
    def plot_policies(
            self,
            save_dir: str = '../plots/policy/'
    ):

        policy_plots = PolicyPlots(self.world)

        restaurant_reopening_plot.policy_plots.plot_restaurant_reopening()
        restaurant_reopening_plot.plot()
        restaurant_reopening_plot.savefig(save_dir + 'restaurant_reopening.png', dpi=150, bbox_inches='tight')
    
        school_reopening_plot = policy_plots.plot_school_reopening()
        school_reopening_plot.plot()
        school_reopening_plot.savefig(save_dir + 'school_reopening.png', dpi=150, bbox_inches='tight')

    
    def plot_all(self):

        self.plot_policies()

    
