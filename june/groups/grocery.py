import random
from enum import IntEnum

import numpy as np
from sklearn.neighbors._ball_tree import BallTree

from june.groups import Group


class Grocery(Group):
    """
    The Grocery class represents a grocery, and treats all people in it
    without any distinction of their role.

    There are two sub-groups:
    0 - workers
    1 - guests
    """

    class GroupType(IntEnum):
        workers   = 0
        customers = 1

    def __init__(self, grocery_id=1, position=None):
        super().__init__("Grocery_%03d" % grocery_id, "grocery")
        self.id = grocery_id
        self.position = position

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "grocery"


class Groceries:
    """
    Contains all groceries for the given area, and information about them.
    """
    def __init__(self, geography, ratio=760.):
        self.geography = geography
        self.fill_parameters()
        self.init_members(float(ratio))

    def init_parameters():
        self.daily_probability = 0.15
        self.male_probability  = 0.2
        self.both_adults_go    = 0.2

    def init_members():
        index   = 0
        n_areas = 0
        for super_area in self.geography.super_areas.members:
            self.fill_area_with_groceries(n_total,float(ratio))
            n_areas += 1
        print("Initialised ",index," groceries in",n_areas,"areas.")
            
    def fill_area_with_groceries(self,index,ratio):
        n_residents = 0
        for area in super_area.areas:
            n_residents = area.n_residents
        n_mean    = n_residents/ratio
        n_actual  = round(np.random.poisson(n_mean))
        groceries = []
        while n_actual>0:
            groceries.append(Grocery(index,area.coordinates))
            index += 1
        self.members[area] = grocerys

    def send_people_to_groceries(self):
        for super_area, groceries in self.members.items():
            for area in super_area.members:
                for households in area.household:
                    if random.random()<self.daily_probability:
                        grocery = np.random.choice(groceries)
                        self.send_people_in_household_to_grocery(household,grocery)

    def send_people_in_household_to_grocery(self,household,grocery):
        # I will ignore all male-female asymmetry here and the case of young kids
        # accompanying their parents
        customer = household.select_random_parent()
        if customer.active_group==None:
            grocery.add(customer, Grocery.GroupType.customers)
    
# 2019: 87.141 grocery stores in the uk.
# assuming 66M people in the UK this means there is 1 grocery shop for about 760 people, or
# about 11 in each of the 7201 msoareas in England and Wales (I subtractec 10% of groceries
# in Scotland and Northern Ireland, pretty much by population).
# I would imagine that we could correlate this with socio-economic indices (more shops for
# richer people), but for the moment we just do a Poissonian with a mean given by the ratio
# of people in the area/760.
# weekly shopping frequency in supermarkets:
# (https://www.statista.com/statistics/495444/weekly-frequency-of-supermarket-shopping-united-kingdom-uk/)
# 1-2   56%
# 3-4   30%
# 5-6    9%
# 7-8    2%
# relatively well fitted with prob 0.15 for each (daily) call:

