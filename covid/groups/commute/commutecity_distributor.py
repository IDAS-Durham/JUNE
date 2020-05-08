import numpy as np

class CommuteCityDistributor:
    """
    Distirbute people to cities based on where they work
    """

    def __init__(self, commutecities, msoa):
        """
        commutecities: members of CommuteCities class
        msoa: members of the MSOArea class
        """
        self.commutecities = commutecities
        self.msoas = msoas

    def distribute_people(self):

        for commutecity in self.commutecities:
            metro_msoas = commutecity.metro_msoas

            for msoa in self.msoas:
                if msoa.name in metro_msoa:
                    for person in msoa.work_people:
                        # assign people who commute to the given city
                        commutecity.passengers.append(person)
            
            
            
            
