from collections import Counter
import pickle
import pytest



def test_number_schools(world_ne):
    """ 
    Check the number of schools is right
    """
    inputs = world_ne.inputs
    assert len(world_ne.schools.members) == len(inputs.school_df)


def test_all_kids_school(world_ne):
    """
    Check that all kids in ages between 5 and 17 are assigned a school 
    """
    KIDS_LOW = 5
    KIDS_UP = 17
    lost_kids = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].people)):
            if (world_ne.areas.members[i].people[j].age >= KIDS_LOW) and (
                world_ne.areas.members[i].people[j].age <= KIDS_UP
            ):
                if world_ne.areas.members[i].people[j].school is None:
                    lost_kids += 1

    assert lost_kids == 0

def test_only_kids_school(world_ne):
    """
    Check that all kids in ages between 5 and 17 are assigned a school 
    """
    ADULTS_LOW = 20 
    schooled_adults = 0
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].people)):
            if world_ne.areas.members[i].people[j].age >= ADULTS_LOW:
                if world_ne.areas.members[i].people[j].school is not None:
                    schooled_adults += 1

    assert schooled_adults == 0

