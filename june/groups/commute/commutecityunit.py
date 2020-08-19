from june.groups.group import Group, Supergroup

import numpy as np

class CommuteCityUnit(Group):

    def __init__(self, city, is_peak):
        super().__init__()
        
        self.city = city
        self.is_peak = is_peak
        self.max_passengers = 50
        self.no_passengers = 0

    
class CommuteCityUnits(Supergroup):

    def __init__(self, commutecities):

        super().__init__()

        self.commutecities = commutecities
        self.members = []

    def init_units(self):

        ids = 0
        for commutecity in self.commutecities:
            no_passengers = len(commutecity.commute_internal)
            no_units = int(float(no_passengers)/50) + 1

            peak_not_peak = np.random.choice(2,no_units,[0.8,0.2])
            
            for i in range(no_units):
                commutecity_unit = CommuteCityUnit(
                    city = commutecity.city,
                    is_peak = peak_not_peak[i]
                )

                self.members.append(commutecity_unit)
                commutecity.commutecityunits.append(commutecity_unit)
                
            ids += 1
