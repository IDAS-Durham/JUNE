import random
from enum import IntEnum

import numpy as np
from sklearn.neighbors._ball_tree import BallTree

from june.groups import Group


class Pub(Group):
    """
    The Pub class represents a pub, and treats all people in it
    without any distinction of their role.

    There are two sub-groups:
    0 - workers
    1 - guests
    """

    class GroupType(IntEnum):
        workers = 0
        guests = 1

    def __init__(self, position=None):
        super().__init__()
        self.position = position

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "pub"


class Pubs:
    """
    Contains all pubs for the given area, and information about them.
    """
    def __init__(self, geography, pub_df=None, box_mode=False):
        self.geography = geography
        self.box_mode  = box_mode
        self.init_parameters()
        self.init_members(pub_df)
        
    def init_parameters(self):
        # maximal distance of customer going to a pub, with a minimum of five choices
        self.maxdistance = 5.
        self.minchoices  = 5
        # these parameters steer the sociology of the pub goers
        self.pub_weekend_ratio      = 0.1
        self.pub_weekday_ratio      = 0.05
        self.pub_female_ratio       = 0.5
        self.pub_over35_ratio       = 0.5
        self.pub_over55_ratio       = 0.3
        self.full_household_in_pub  = 0.5
        self.adults_in_pub          = 0.5
        self.pub_female_probability = self.pub_female_ratio/(1.+self.pub_female_ratio) 

    def init_members(self,pub_df):
        self.members = {}
        if self.box_mode:
            if self.geography==None:
                tag = "box"
            else:
                tag = self.geography
            self.members[tag] = []
            self.members[tag].append(Pub(1,np.array([0.001,0.])))  # "The Blue Horse"
            self.members[tag].append(Pub(2,np.array([0.,0.001])))  # "The Red Donkey"
        else:
            pub_tree, pub_list = self.create_pub_tree_and_list(pub_df)
            self.fill_areas_pub_map(self.geography.super_areas.members, pub_tree, pub_list)

    def create_pub_tree_and_list(self, pub_df):
        pub_tree = BallTree(
            np.deg2rad(pub_df[["Latitude", "Longitude"]].values), metric="haversine"
        )
        pub_list = []
        for row in range(pub_df.shape[0]):
            position = [pub_df.iloc[row]["Latitude"], pub_df.iloc[row]["Longitude"]]
            pub_list.append(Pub(len(pub_list), position))
        return pub_tree, pub_list

    def fill_areas_pub_map(self,areas,pub_tree,pub_list):
        for area in areas:
            angles, indices = pub_tree.query(
                np.deg2rad(area.coordinates.reshape(1, -1)), 20, sort_results=True
            )
            pubs = []
            for angle, index in zip(angles[0],indices[0]):
                if (angle * 6500. < self.maxdistance or
                    len(pubs) < self.minchoices):
                    pubs.append(pub_list[index])
            self.members[area] = pubs

    def send_people_to_pub(self):
        for area, pubs in self.members.items():
            npeople = self.fix_number_of_customers(area)
            while npeople>0:
                pub      = np.random.choice(pubs)
                customer = self.select_customer(area)
                pub.add(customer, Pub.GroupType.guests)
                self.add_household_members(pub, customer)
                npeople -= 1
            
    def fix_number_of_customers(self, area):
        nmean = len(area.adult_active_females)+len(area.adult_active_males)
        if self.geography.timer.weekend:
            nmean *= self.pub_weekend_ratio
        else:
            nmean *= self.pub_weekday_ratio
        return round(np.random.poisson(nmean))
    
    def select_customer(self,area):
        customer = None
        while customer==None:
            if random.random()<self.pub_female_probability:
                customer = np.random.choice(area.adult_active_females)
            else:
                customer = np.random.choice(area.adult_active_males)
            if (customer.carehome!=None or
                customer.active_group!=None or
                random.random()>self.make_weight(customer)):
                customer = None
        return customer

    def add_household_members(self,pub,customer):
        if (self.geography.timer.weekend and
            random.random() < self.full_household_in_pub and
            customer.household!=None):
            for person in customer.household.people:
                if person!=customer:
                    pub.add(person, Pub.GroupType.guests)
        elif (not self.geography.timer.weekend and
              random.random() < self.adults_in_pub and
              customer.household!=None):
            for person in customer.household.people:
                if person!=customer and person.age >= 18:
                    pub.add(person, Pub.GroupType.guests)            
               
                
    def make_weight(self, customer):
        weight = 1.
        if customer.age >= 35 and customer.age < 55:
            weight *= self.pub_over35_ratio
        elif customer.age >= 55:
            weight *= self.pub_over55_ratio
        return weight
            
# about 30% of UK adults (44%M, 20%F) visit a pub weekly according to
# https://www.statista.com/statistics/388045/weekly-pub-visits-adults-united-kingdom/
# https://howtorunapub.co.uk/uk-pub-customer-demographics-behaviours/
# will assume that WE visits are abot twice as frequent as weekdays -
# so 6% of population visit on Saturday/Sunday and 3% visit weekdays
#
# about 50% of pub goers are age 18-34, 32% are 34-55, 18% are 55 or over,
# gender ratio 66%(M)-34%(F),
# groups going to the pub: 23% familes, 22% couples (-> will treat both as households)
# https://www.cga.co.uk/wp-content/uploads/2019/02/CGA_00146-Pub-Report-12page.pdf

