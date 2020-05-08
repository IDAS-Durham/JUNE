from june.world import World
import pandas as pd
from june.inputs import Inputs
from june.groups.hospitals import hospital

def test_all_areas_to_hospital(world_ne):
    '''
    check if all areas have a nearby hospital
    '''
    N_neighbours = 1
    world = world_ne
    ip = world_ne.inputs
    hospitals = hospital.Hospitals(ip.hospital_df)
    for i in range(len(world.areas.members)):
        Area =  world.areas.members[i]
        nearest_hospital = hospitals.get_closest_hospital(Area,k=N_neighbours)
        assert nearest_hospital[0].shape == (N_neighbours,)
