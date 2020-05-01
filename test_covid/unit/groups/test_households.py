import numpy as np
import os


def test__no_lonely_children(world_ne):
    """
    Check there ar eno children living without adults
    """
    only_children = 0
    for household in world_ne.households.members:
        has_children = False
        has_adults = False
        for person in household.people:
            if person.age < 18:
                has_children = True
            if person.age >= 18:
                has_adults = True
        if has_children and not has_adults:
            only_children += 1

    assert only_children == 0


def test__no_homeless(world_ne):
    """
    Check that no one belonging to an are is left without a house
    """
    total_in_carehomes = 0
    for carehome in world_ne.carehomes.members:
        total_in_carehomes += len(carehome.people)
    total_in_households = total_in_carehomes
    for i in range(len(world_ne.areas.members)):
        for j in range(len(world_ne.areas.members[i].households)):
            total_in_households += len(world_ne.areas.members[i].households[j].people)

    assert total_in_households == len(world_ne.people.members)

