from june.inputs import Inputs 
import matplotlib.pyplot as plt
import numpy as np
import pickle
import seaborn as sns


sns.set_context('paper')

def estimate_age_composition(world):

    attribute = 'age'
    decoder = getattr(world, "decoder_" + attribute)
    n_age = np.zeros((len(world.areas.keys()), len(decoder)))
    for key in world.areas.keys():
        for j in world.areas[key].people.keys():
            n_age[key, getattr(world.areas[key].people[j], attribute)] += 1
    return np.sum(n_age, axis=0)


if __name__=='__main__':

    WORLD_PATH = '/cosma7/data/dp004/dc-quer1/world.pkl'
    inputs = Inputs()
    with open(WORLD_PATH, 'rb') as f:
            world = pickle.load(f)

    age_est = estimate_age_composition(world)

    ages_df = inputs.read_ages_df(freq=False)
    age = ages_df.sum()

    width = 0.3
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.bar(np.arange(len(age.index))-width,age.values,
                width,
                label='Estimated from Census 2011',
                alpha=0.7
        )
    ax.bar(age.index,age_est,
        width,
        label='Simulation',
        alpha=0.7
       )
    plt.xticks(rotation='vertical')
    plt.ylabel('Bin counts')
    plt.xlabel('Age bands')
    plt.autoscale(tight=True)
    plt.legend()
    plt.subplots_adjust(left=0.3, right=0.9, bottom=0.4, top=0.9)

    plt.savefig('../images/ages_oa.png',
                   dpi=250,
                   bbox_to_anchor='tight'
            )



