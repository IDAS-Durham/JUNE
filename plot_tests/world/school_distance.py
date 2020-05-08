from collections import Counter
import pandas as pd
from june.inputs import Inputs 
from june.world import World
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import numpy as np
import math

sns.set_context('paper')


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


def kids_school_distance(world, KIDS_LOW=5, KIDS_UP=19):

    distance_school = []
    lost_kids = 0 
    for i in range(len(world.areas.members)):
        for j in range(len(world.areas.members[i].people)):
            if (world.areas.members[i].people[j].age >= KIDS_LOW) and (world.areas.members[i].people[j].age <= KIDS_UP):

                try:
                    school_coordinates = world.areas.members[i].people[j].school.coordinates
                    distance_school.append(
                                distance(world.areas.members[i].coordinates,
                                    school_coordinates)
                                )
                except:
                    lost_kids += 1
    print(f'CAREFUL! There are {lost_kids} lost kids')
    return distance_school

if __name__=='__main__':

    world = World.from_pickle()

    distance_school = kids_school_distance(world)
    distance_young = kids_school_distance(world, 5, 11) 
    distance_old = kids_school_distance(world, 12, 19)

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
            label = '5 - 11 years old',
            alpha=0.3,
            )
    plt.hist(
            distance_old, 
            log=True,
            label = '12 - 19 years old',
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


