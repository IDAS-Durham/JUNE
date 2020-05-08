import matplotlib.pyplot as plt
import numpy as np
import pickle
from collections import Counter
import pandas as pd
from june.inputs import Inputs 
import seaborn as sns

sns.set_context('paper')


def load_world(path2world):

    with open(path2world, 'rb') as f:
        world = pickle.load(f)
    return world

def estimate_household_composition(world):
    household_composition_est = []
    for area in world.areas.values():
        for household in area.households.values():
            household_composition_est.append(world.decoder_household_composition[household.household_composition])

    household_composition_dict = dict(Counter(household_composition_est))
    return household_composition_dict


if __name__ == '__main__':

    world = load_world('/cosma7/data/dp004/dc-quer1/world.pkl')
    width = 0.3
    inputs = Inputs()
    ages_df = inputs.read_ages_df(freq=False)
    comp_people_df = inputs.read_household_composition_people(ages_df)
    households_df = inputs.people_compositions2households(comp_people_df,
                                                             freq=False)
    n_households = households_df.sum()

    household_composition_dict = estimate_household_composition(world)

    results = []
    for key in list(n_households.index):
        results.append([n_households.loc[key], household_composition_dict[key]])
    results = np.asarray(results)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(np.arange(len(n_households.index))-width,results[:,0],
                   width,
                   label='Estimated from Census 2011',
                   alpha=0.7
            )
    ax.bar(n_households.index,results[:,1],
                   width,
                   #color='indianred',
                   label='Simulation',
                  alpha=0.7
            )
    plt.xticks(rotation='vertical')
    plt.ylabel('Bin counts')
    plt.xlabel('Household composition')
    plt.autoscale(tight=True)
    plt.legend()
    plt.subplots_adjust(left=0.3, right=0.9, bottom=0.4, top=0.9)

    plt.savefig('../images/household_composition.png',
                       dpi=250,
                       bbox_to_anchor='tight'
                )
    


