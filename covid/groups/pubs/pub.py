import random
from enum import IntEnum

import numpy as np
from sklearn.neighbors._ball_tree import BallTree

from covid.groups import Group


class Pub(Group):
    """
    The Pub class represents a pub, and treats all people in it
    without any distinction of their role.

    There are two sub-groups:
    0 - workers
    1 - guestss
    """

    class GroupType(IntEnum):
        workers = 0
        guests = 1

    def __init__(self, pub_id=1, position=None):
        super().__init__("Pub_%03d" % pub_id, "pub")
        self.id = pub_id
        self.position = position

    def set_active_members(self):
        for person in self.people:
            if person.active_group is None:
                person.active_group = "pub"


class Pubs:
    """
    Contains all pubs for the given area, and information about them.
    """

    def __init__(self, world, pub_df=None, box_mode=False):
        self.world = world
        self.box_mode = box_mode
        self.members = []
        # maximal distance of customer going to a pub, with a minimum
        # of five choices
        self.maxdistance = 5.
        self.minchoices = 5
        if not self.box_mode:
            self.pub_trees = self.create_pub_trees(pub_df)
        else:
            self.members.append(Pub("The Blue Horse"))
            self.members.append(Pub("The Red Donkey"))
        print("initialized ", len(self.members), " pubs.")

    def create_pub_trees(self, pub_df):
        # print (pub_df[["Latitude", "Longitude"]].values)
        pub_tree = BallTree(
            np.deg2rad(pub_df[["Latitude", "Longitude"]].values),
            metric="haversine"
        )
        counter = 0
        for row in range(pub_df.shape[0]):
            position = [pub_df.iloc[row]["Latitude"], pub_df.iloc[row]["Longitude"]]
            self.members.append(Pub(counter, position))
            counter += 1
        return pub_tree

    def get_nearest(self, area):
        if self.box_mode:
            return self.mambers[random.choice(np.arange(len(self.members) - 1))]
        else:
            angles, indices = self.get_closest_pubs(area, 100)
        index = 0
        pubs = []
        for angle in angles[0]:
            if (angle * 6500. < self.maxdistance or
                    len(pubs) < self.minchoices):
                pubs.append(self.members[index])
            index += 1
        return pubs

    def get_closest_pubs(self, area, k):
        pub_tree = self.pub_trees
        return pub_tree.query(
            np.deg2rad(area.coordinates.reshape(1, -1)), k=k, sort_results=True
        )


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


class PubFiller:
    def __init__(self, world):
        self.world = world
        self.allpubs = self.world.pubs
        self.pub_weekend_ratio = 0.1
        self.pub_weekday_ratio = 0.05
        self.pub_female_ratio = 0.5
        self.pub_over35_ratio = 0.5
        self.pub_over55_ratio = 0.3
        self.full_household_in_pub = 0.5
        self.adults_in_pub = 0.5

    def fix_number(self, area):
        nmean = len(area.people)
        if self.world.timer.weekend:
            nmean *= self.pub_weekend_ratio
        else:
            nmean *= self.pub_weekday_ratio
        return round(np.random.poisson(nmean))

    def make_weight(self, customer):
        if customer.age < 18:
            return 0.
        weight = 1.
        if customer.age >= 35 and customer.age < 55:
            weight *= self.pub_over35_ratio
        elif customer.age >= 55:
            weight *= self.pub_over55_ratio
        if customer.sex == 1:
            weight *= self.pub_female_ratio
        return weight

    def place(self, customer):
        if self.make_weight(customer) < np.random.random():
            return False
        pub = np.random.choice(self.pubs)
        pub.add(customer, Pub.GroupType.guests)
        if self.world.timer.weekend and random.random() < self.full_household_in_pub:
            for person in customer.household.people:
                if person != customer:
                    pub.add(person, Pub.GroupType.guests)
        elif not (self.world.timer.weekend) and random.random() < self.adults_in_pub:
            for person in customer.household.people:
                if person != customer and person.age >= 18:
                    pub.add(person, Pub.GroupType.guests)
        return True

    def fill(self, area):
        ncustomers = self.fix_number(area)
        self.pubs = self.allpubs.get_nearest(area)
        while ncustomers > 0:
            if self.place(np.random.choice(area.people)):
                ncustomers -= 1
        # for pub in self.pubs:
        #    print ("pub with",len(pub.people)," customers:")
        #    for person in pub.people:
        #        print ("   --> ",person.id,"(",person.age,", ",person.sex,")")
