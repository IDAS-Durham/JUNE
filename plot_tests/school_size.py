from collections import Counter
import pandas as pd
from covid.inputs import Inputs 
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

sns.set_context('paper')


def load_world(path2world):

    with open(path2world, 'rb') as f:
        world = pickle.load(f)
    return world

def school_size(world):
    sizes, sizes_est = [], []
    for i in world.schools.keys():
        if len(world.schools[i].pupils) >0:
            sizes.append(world.schools[i].n_pupils_max)
            sizes_est.append(len(world.schools[i].pupils))

    return sizes, sizes_est

if __name__=='__main__':
    WORLD_PATH = '/cosma7/data/dp004/dc-quer1/world.pkl'
    with open(WORLD_PATH, 'rb') as f:
            world = pickle.load(f)

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


