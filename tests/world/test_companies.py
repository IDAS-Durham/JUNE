from collections import Counter
from covid.world import World
import numpy as np
import pandas as pd
from covid.inputs import Inputs
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

def test_():
    """
    Check that all kids in ages between 5 and 17 are assigned a school 
    """
    world = World.from_pickle()
    KIDS_LOW = 5
    KIDS_UP = 17
    lost_kids = 0
    for i in range(len(world.areas.members)):
        for j in range(len(world.areas.members[i].people)):
            if (world.areas.members[i].people[j].age >= KIDS_LOW) and (
                world.areas.members[i].people[j].age <= KIDS_UP
            ):
                if world.areas.members[i].people[j].school is None:
                    lost_kids += 1

    assert lost_kids == 0
