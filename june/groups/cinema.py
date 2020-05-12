import random
from enum import IntEnum

import numpy as np
from sklearn.neighbors._ball_tree import BallTree

from june.groups import Group


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
        super().__init__("Cinema_%03d" % cinema_id, "cinema")
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
    def __init__(self, geography, cinema_df=None,postcode_df=None):
        self.geography = geography
        cinema_postcode_df = pd.merge(cinema_df, postcodes,
                                      left_on="postcode", right_on="postcode")
        self.init_members(cinema_postcode_df)
        
    def init_members(self,cinema_postcode_df):
        self.members = {}
        cinema_tree, cinema_list = self.create_cinema_tree_and_list(cinema_postcode_df)
        self.fill_areas_cinema_map(self.geography.super_areas.members, cinema_tree, cinema_list)

    def create_cinema_tree_and_list(self, cinema_df):
        cinema_tree = BallTree(
            np.deg2rad(cinema_postcode_df[["latitude", "longitude"]].values),
            metric="haversine"
        )
        cinema_list = []
        for row in range(cinema_df.shape[0]):
            position = [cinema_df.iloc[row]["Latitude"], cinema_df.iloc[row]["Longitude"]]
            cinema_list.append(Cinema(len(cinema_list), position))
        return cinema_tree, cinema_list

    def fill_areas_cinema_map(self,areas,cinema_tree,cinema_list):
        for area in areas:
            angles, indices = cinema_tree.query(
                np.deg2rad(area.coordinates.reshape(1, -1)), 1, sort_results=True
            )
            self.members[area] = cinema_list[index]

    def send_people_to_cinema(self):  
        pass
            
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

