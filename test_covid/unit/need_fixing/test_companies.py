from collections import Counter
from covid.world import World
import numpy as np
import pandas as pd
from covid.inputs import Inputs
import seaborn as sns
import pickle
import pytest

sns.set_context("paper")


def test_company_size():
    """
    """
    in_compsize_distr = world.inputs.companysize_df.sum(axis='rows')
    in_compsize_distr = in_compsize_distr.to_frame(name="in_counts")
    in_compsize_distr = in_compsize_distr.reset_index()
    in_compsize_distr = in_compsize_distr.rename(columns={"index": "bins"})

    out_compsize_distr = np.zeros(len(world.companies.members))
    for i, company in enumerate(world.companies.members):
        out_compsize_distr[i] = company.n_employees
        
    bins = np.array([0,9,19,20,50,100,250,500,1000,999999])
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


    in_compsize_distr = in_compsize_distr.rename(columns={"in_counts": "counts"})
    out_compsize_distr = out_compsize_distr.rename(columns={"out_counts": "counts"})
    in_compsize_distr["src"] = ["input"] * len(in_compsize_distr.index.values)
    out_compsize_distr["src"] = ["output"] * len(out_compsize_distr.values)

    compsize_distr = pd.concat([in_compsize_distr, out_compsize_distr], axis=0)


def test_company_number_per_msoa():
    """ 
    Check the number of companies in the world is correct

    Problem:
        This test will faile if the simulated area is not
        enough isolated and companies are drawing to many
        people from outside the simulated area.
    """
    world = World.from_pickle()
    inputs = Inputs()
    msoas = np.unique(inputs.oa2msoa_df["MSOA11CD"].values)
    assert (
        abs(1 - len(world.companies.members) / \
            world.inputs.companysize_df.sum(axis=1).sum()
        ) < 0.15
    )

def test_company_sex_ratio():
    """
    """
    world = World.from_pickle()
    inputs = Inputs()

    comp_size_bins = [0,9,19,20,50,100,250,500,1000,999999]  #TODO don't hardcode
    
    comp_sizes = np.zeros(len(world.companies.members))
    for i, company in enumerate(world.companies.members):
        comp_sizes[i] = company.n_employees_max

    world_hist = np.histogram(comp_sizes, bins=comp_size_bins, normed=True)[0]
    input_hist = worksize_df.sum(axis=0).values / worksize_df.sum(axis=0).sum()

    #TODO judge the difference in distribution


#def test_company_sex_ratio():
#    """
#    """
