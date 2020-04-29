from collections import Counter
import pickle
import pytest

def test_number_carehomes(world_ne):
    """ 
    Check the number of schools is right
    """
    inputs = world_ne.inputs
    assert len(world_ne.carehomes.members) == len(inputs.carehomes_df[inputs.carehomes_df['N_carehome_residents'] > 0])


def test_no_kids_carehome(world_ne):
    """
    Check that kids are not assigned to carehomes
    """
    KIDS_LOW = 0
    KIDS_UP = 18
    lost_kids = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].people)):
            if (world_ne.areas.members[i].people[j].age >= KIDS_LOW) and (
                world_ne.areas.members[i].people[j].age <= KIDS_UP
            ):
                if world_ne.areas.members[i].people[j].carehome is not None:
                    lost_kids += 1

    assert lost_kids == 0


def test_n_carehome_residents(world_ne):

    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].carehomes)):
            assert world_ne.inputs.carehomes_df.loc[world_ne.areas.members[i].name] == world_ne.areas.members[i].carehomes.members[j].n_carehome_residents
            assert world_ne.inputs.carehomes_df.loc[world_ne.areas.members[i].name] == len(world_ne.areas.members[i].carehomes.members[j].people)

