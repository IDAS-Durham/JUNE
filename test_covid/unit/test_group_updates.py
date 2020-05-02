from collections import Counter
from covid.groups import *
import pickle
import os
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from covid import World

def test__everyone_is_in_school_household(world_ne):
    world_ne.set_active_group_to_people(['schools'])
    #world_ne.set_allpeople_free()
    world_ne.set_active_group_to_people(['households'])
    for person in world_ne.people.members:
        should_be_active = 'school' if person.school is not None else 'household' 
        assert person.active_group == should_be_active
        assert person.active_group is not None
    world_ne.set_allpeople_free()

def test__everyone_is_in_company(world_ne):
    world_ne.set_active_group_to_people(['companies'])
    for person in world_ne.people.members:
        should_be_active = 'company' if person.industry is not None else None
        assert person.active_group == should_be_active
    world_ne.set_allpeople_free()


def test__everyone_is_active_somewhere(world_ne):
    world_ne.set_active_group_to_people(['schools', 'households'])
    for person in world_ne.people.members:
        assert person.active_group is not None
    world_ne.set_allpeople_free()

def test__everyone_is_freed(world_ne):
    active_groups = world_ne.timer.active_groups()
    world_ne.set_allpeople_free()
    for person in world_ne.people.members:
        assert person.active_group == None
    world_ne.set_allpeople_free()

def test__everyone_is_in_school(world_ne):
    active_groups = world_ne.timer.active_groups()
    world_ne.set_allpeople_free()
    world_ne.set_active_group_to_people(['schools'])
    for person in world_ne.people.members:
        if person.school is not None:
            assert person.active_group == 'school' 
    world_ne.set_allpeople_free()


def find_random_in_school(world_ne):
    for person in world_ne.people.members:
        if person.school is not None:
            selected_person = person
            break
    return selected_person

def find_random_in_company(world_ne):
    for person in world_ne.people.members:
        if person.industry is not None:
            selected_person = person
            break
    print(f'Selected person industry : {selected_person.industry}')
    return selected_person

def test__set_active_group_workers(world_ne):
    selected_person = find_random_in_company(world_ne) 
    print(f'Industry : {selected_person.industry}')
    world_ne.set_allpeople_free()
    for day in world_ne.timer:
        active_groups = world_ne.timer.active_groups()
        world_ne.set_active_group_to_people(active_groups)
        should_be_active = 'company' if 'companies' in active_groups else 'household' 
        assert selected_person.active_group == should_be_active 
        world_ne.set_allpeople_free()
        assert selected_person.active_group == None
        if day > 10:
            break
    world_ne.set_allpeople_free()


def test__set_active_group_pupils(world_ne):
    selected_person = find_random_in_school(world_ne) 
    world_ne.set_allpeople_free()
    print(f'School = {selected_person.school}')
    print(f'Household = {selected_person.household}')
    for day in world_ne.timer:
        active_groups = world_ne.timer.active_groups()
        print('active groups ', active_groups)
        world_ne.set_active_group_to_people(active_groups)
        should_be_active = 'school' if 'schools' in active_groups else 'household' 
        assert selected_person.active_group == should_be_active 
        world_ne.set_allpeople_free()
        assert selected_person.active_group == None
        if day > 10:
            break
    world_ne.set_allpeople_free()

if __name__=='__main__':
    config_path = os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)
            ),
            "..",
            "config_ne.yaml"
    )
    world = World(config_path, box_mode=False)

    test__set_active_group_pupils(world)
    test__set_active_group_workers(world)

    
