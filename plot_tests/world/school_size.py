from collections import Counter
import pandas as pd
from covid.inputs import Inputs 
from covid.world import World
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

sns.set_context('paper')



def school_size(world):
    sizes, sizes_est = [], []
    for i in range(len(world.schools.members)):
        if len(world.schools.members[i].people) >0:
            sizes.append(world.schools.members[i].n_pupils_max)
            sizes_est.append(len(world.schools.members[i].people))

    return sizes, sizes_est

if __name__=='__main__':
    world = World.from_pickle()
    size_school, size_school_est = school_size(world)

    bins =plt.hist(size_school, 
             log=True, label='Estimated from school census',
             alpha=0.3)
    plt.hist(size_school_est, 
             bins= bins[1],
             log=True,
            label='Simulation',
             alpha=0.3)
    plt.xlabel('School size [number of students]')
    plt.ylabel('Bin count')
    plt.legend()
    plt.savefig('../images/school_size.png',
                       dpi=250,
                       bbox_to_anchor='tight'
                )


