from collections import Counter
from june.world import World
import numpy as np
import pandas as pd
from june.inputs import Inputs
import seaborn as sns
import pickle
import pytest

sns.set_context("paper")


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
