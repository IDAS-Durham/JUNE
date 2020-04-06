from collections import Counter
import pandas as pd
from covid.inputs import Inputs 
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import numpy as np
import math

sns.set_context('paper')


def load_world(path2world):

    with open(path2world, 'rb') as f:
        world = pickle.load(f)
    return world


def distance(origin, destination):
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371 # km

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c 

    return d # km


def kids_school_distance(world, KIDS_LOW=1, KIDS_UP=6):

    distance_school = []
    lost_kids = 0 
    for i in world.areas.keys():
        for j in world.areas[i].people.keys():
            if (world.areas[i].people[j].age >= KIDS_LOW) and (world.areas[i].people[j].age <= KIDS_UP):
                try:
                    school_coordinates = world.areas[i].people[j].school.coordinates
                    distance_school.append(
                                    distance(world.areas[i].coordinates,
                                        school_coordinates)
                                    )
                except:
                    lost_kids += 1
    print(f'CAREFUL! There are {lost_kids} lost kids')
    return distance_school

if __name__=='__main__':

    WORLD_PATH = '/cosma7/data/dp004/dc-quer1/world.pkl'
    with open(WORLD_PATH, 'rb') as f:
            world = pickle.load(f)

    distance_school = kids_school_distance(world)
    distance_young = kids_school_distance(world, 1, 3)
    distance_old = kids_school_distance(world, 4, 6)

    fig = plt.figure()
    plt.hist(
            distance_school, 
            log=True,
            alpha=0.3,
            label = '5 - 19 years old'
            )
    plt.hist(
            distance_young, 
            log=True,
            label = '5 - 14 years old',
            alpha=0.3,
            )
    plt.hist(
            distance_old, 
            log=True,
            label = '15 - 19 years old',
            alpha=0.3,
            )
    plt.legend()
    plt.text(45,5e3, f'5 - 19 Mean {np.mean(distance_school):.2f} km \n (Official data ~3 km)')
    plt.text(45,1e3, f'5 - 14 Mean {np.mean(distance_young):.2f} km')# \n (Official data ~3 km)')
    plt.text(45,5e2, f'15 - 19 Mean {np.mean(distance_old):.2f} km')

    plt.xlabel('Distance travelled to school [km]')
    plt.ylabel('Bin count')

    plt.savefig('../images/distance2school.png',
                       dpi=250,
                       bbox_to_anchor='tight'
                )


