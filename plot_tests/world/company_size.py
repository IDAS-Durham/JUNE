from collections import Counter
import pandas as pd
from covid.inputs import Inputs 
from covid.world import World
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

sns.set_context('paper')



def company_size(world):
    # get company size distribution from input data
    in_compsize_distr = world.inputs.companysize_df.sum(axis='rows')
    in_compsize_distr = in_compsize_distr.to_frame(name="in_counts")
    in_compsize_distr = in_compsize_distr.reset_index()
    in_compsize_distr = in_compsize_distr.rename(columns={"index": "bins"})

    # get company size distribution from output data
    out_compsize_distr = np.zeros(len(world.companies.members))
    for i, company in enumerate(world.companies.members):
        out_compsize_distr[i] = company.n_employees
    bins = np.array([0,9,19,20,50,100,250,500,1000,999999]) #TODO can be done without hardcode
    inds = np.digitize(out_compsize_distr, bins)
    bins, counts = np.unique(inds, return_counts=True)
    out_compsize_distr = pd.DataFrame(
        data=np.array([bins, counts]).T,
        columns=['size','out_counts'],
    )
    out_compsize_distr= pd.merge(
        in_compsize_distr,
        out_compsize_distr,
        left_index=True,
        right_index=True,
        how='left',
    )
    out_compsize_distr = out_compsize_distr.fillna(0)
    out_compsize_distr = out_compsize_distr.drop(["size", "in_counts"], axis=1)

    # merge the two pd.DataFrames into one
    in_compsize_distr = in_compsize_distr.rename(columns={"in_counts": "counts"})
    out_compsize_distr = out_compsize_distr.rename(columns={"out_counts": "counts"})
    in_compsize_distr["src"] = ["input"] * len(in_compsize_distr.index.values)
    out_compsize_distr["src"] = ["output"] * len(out_compsize_distr.values)
    compsize_distr = pd.concat([in_compsize_distr, out_compsize_distr], axis=0)
    return compsize_distr

if __name__=='__main__':
    world = World.from_pickle()
    compsize_distr = company_size(world)

    sns.catplot(
        x="bins",
        y="counts",
        hue="src",
        data=compsize_distr,
        height=6,
        kind="bar",
        palette="muted",
    )



