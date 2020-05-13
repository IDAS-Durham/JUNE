import random
from enum import IntEnum
import pandas as pd
import numpy as np
from sklearn.neighbors._ball_tree import BallTree

from june.groups import Group
from june.groups.household import Household

class Cinema(Group):
    """
    The Cinema class represents a cinema, and treats all people in it
    without any distinction of their role.

    There are two sub-groups:
    0 - workers
    1 - guests
    """

    class GroupType(IntEnum):
        workers = 0
        guests = 1

    def __init__(self, cinema_id=1, position=None):
        super().__init__()
        self.id = cinema_id
        self.position = position

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "cinema"


class Cinemas:
    """
    Contains all cinemas for the given area, and information about them.
    """
    def __init__(self, geography, cinemas_df=None):
        self.geography = geography
        self.init_members(cinemas_df)
        
    def init_members(self,cinemas_df):
        self.members = {}
        cinema_tree, cinema_list = self.create_cinema_tree_and_list(cinemas_df)
        self.fill_areas_cinema_map(self.geography.super_areas.members, cinema_tree, cinema_list)

    def create_cinema_tree_and_list(self, cinemas_df):
        cinema_tree = BallTree(
            np.deg2rad(cinemas_df[["latitude", "longitude"]].values),
            metric="haversine"
        )
        cinema_list = []
        for row in range(cinemas_df.shape[0]):
            position = [cinemas_df.iloc[row]["latitude"], cinemas_df.iloc[row]["longitude"]]
            cinema_list.append(Cinema(len(cinema_list), position))
        return cinema_tree, cinema_list

    def fill_areas_cinema_map(self,areas,cinema_tree,cinema_list):
        for area in areas:
            angle, index = cinema_tree.query(
                np.deg2rad(area.coordinates.reshape(1, -1)), 1, sort_results=True
            )
            self.members[area] = [cinema_list[index[0][0]]]


class CinemaFiller:
    """
    Contains all cinemas for the given area, and information about them.
    """
    def __init__(self, cinemas, timer):
        self.cinemas = cinemas
        self.timer   = timer
        self.init_parameters()

    def init_parameters(self):
        self.probKids  = 0.07
        self.probYoung = 0.07
        self.probAdult = 0.03
        self.probOld   = 0.01
        
    def send_people_to_cinemas(self):  
        for super_area, cinemas in self.cinemas.members.items():
            cinema = cinemas[0]
            for area in super_area.areas:
                for household in area.households:
                    if not household.communal:
                        self.add_household_to_customers(household,cinema)

                        
    def add_household_to_customers(self,household,cinema):
        take_all = False
        for kid in household[Household.GroupType.kids]:
            if random.random()<self.probKids:
                take_all = True
                break
        if take_all:
            for person in household.people:
                cinema.add(person, Cinema.GroupType.guests)
            return
        
        take_ad  = False
        take_old = False
        for young_adult in household[Household.GroupType.young_adults].people:
            if random.random()<self.probYoung:
                cinema.add(young_adult, Cinema.GroupType.guests)
        for adult in household[Household.GroupType.adults].people:
            if random.random()<self.probAdult:
                take_ad = True
                break
        for old_adult in household[Household.GroupType.old_adults].people:
            if random.random()<self.probOld:
                take_old = True
                break
        if take_ad:
            for person in household[Household.GroupType.adults].people:
                cinema.add(person, Cinema.GroupType.guests)
        elif take_old:
            for person in household[Household.GroupType.old_adults].people:
                cinema.add(person, Cinema.GroupType.guests)
                
            
# 2019: 176.1 million cinema visitors per year
# (from https://www.cinemauk.org.uk/the-industry/facts-and-figures/uk-cinema-admissions-and-box-office/annual-admissions/)
# age/gender distribution from https://www.statista.com/statistics/296240/age-and-gender-of-the-cinema-audience-uk/
# age range - female/male   visits per week (in thousand)   population in 1.000.000  probability to go
#  7-14        9/10         305 / 338                        9.1                     0.071
# 15-24       13/15         440 / 508                       13.1                     0.072
# 25-34        7/10         237 / 338                       13.3                     0.043
# 35-44        9/ 9         305 / 305                       13.9                     0.044
# 45-54        4/ 6         135 / 203                       13.8                     0.024
# 55+          5/ 3         169 / 102                       17.8                     0.015
#
# we will have to translate this into more meaningful probabilities to go to the cinema when
# including that with kids under 15 probably the full household goes, and that kids 15 and above
# will go with someone else ...
# For this I need to know how the areas treat their residents.

