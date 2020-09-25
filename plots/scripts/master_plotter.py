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
    """
    Master plotting script for paper and validation plots
    Parameters
    ----------
    world
        Preloaded world which can also be passed from the master plotting script
    """

    def __init__(self, world):
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
        "Make all policy plots"

        print ("Setting up policy plots")
        
        policy_plots = PolicyPlots(self.world)

        print ("Plotting restaurant reopening")
        restaurant_reopening_plot.policy_plots.plot_restaurant_reopening()
        restaurant_reopening_plot.plot()
        restaurant_reopening_plot.savefig(save_dir + 'restaurant_reopening.png', dpi=150, bbox_inches='tight')

        print ("Plotting school reopening")
        school_reopening_plot = policy_plots.plot_school_reopening()
        school_reopening_plot.plot()
        school_reopening_plot.savefig(save_dir + 'school_reopening.png', dpi=150, bbox_inches='tight')

        print ("All policy plots finished")
    
    def plot_all(self):

        print ("Plotting the world")
        
        self.plot_policies()

    
