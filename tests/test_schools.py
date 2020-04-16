from collections import Counter
from covid.world import World
import pandas as pd
from covid.inputs import Inputs 
import seaborn as sns
import pickle

sns.set_context('paper')


def test_number_schools():

    #world = load_world('/cosma7/data/dp004/dc-quer1/world.pkl')
    world = World()
    inputs = Inputs()
    assert len(world.schools) ==  len(inputs.school_df)

def test_all_kids_school():
    
    #world = load_world('/cosma7/data/dp004/dc-quer1/world.pkl')
    world = World()
    KIDS_LOW = 1
    KIDS_UP = 5
    lost_kids = 0
    for i in world.areas.members:
        for j in world.areas[i].people.members:
            if (world.areas[i].people[j].age >= KIDS_LOW) and (world.areas[i].people[j].age <= KIDS_UP):
                if world.areas[i].people[j].school is None:
                    lost_kids += 1


    assert lost_kids == 0 



