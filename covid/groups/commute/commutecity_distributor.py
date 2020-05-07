import numpy as np

class CommuteCityDistributor:

    def __init__(self, commutecities, msoa):
        self.commutecities = commutecities
        self.msoas = msoas

    def distribute_people(self):

        for commutecity in self.commutecities:
            metro_msoas = commutecity.metro_msoas

            for msoa in self.msoas:
                if msoa.name in metro_msoa:
                    for person in msoa.work_people:
                        commutecity.passengers.append(person)
            
            
            
            
