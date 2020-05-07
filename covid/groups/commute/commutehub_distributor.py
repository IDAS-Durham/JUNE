import numpy as np


class CommuteHubDistributor:

    def __init__(self, commutecities, commutehubs, people):
        self.commutecities = commutecities
        self.commutehubs = commutehubs
        self.people = people



    def distirbute_people(self):

        for commutecity in self.commutecities:
            work_people = commutecity.passengers

            people_to_commute = []
            for work_person in work_people:
                # check if live AND work in metropolitan area
                if work_person.msoarea in commutecity.metro_msoas:
                    pass

                # if they live outside and commute in then they need to commute through a hub
                else:
                    
