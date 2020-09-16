import numpy as np
from random import shuffle

class CommuteCityUnitDistributor:
    """
    Distirbute people to commutecity units based on the cities they are affiliated to

    Note: This distibutor is dynamic and so should be called at each commutng time step to decide who
          is assigned to which units to determine mixing
    """    

    def __init__(self, commutecities):
        """
        commutecities: (list) members of CommuteCities
        """
        self.commutecities = commutecities


    def distribute_people(self):
        for city in self.commutecities:
            if city.commute_internal:
                # Clear all units of passengers before running
                possible_units = city.commutecityunits
                commuting_people = city.commute_internal
                indices = list(range((len(commuting_people))))
                shuffle(indices)
                people_per_unit = len(commuting_people)//len(possible_units)
                for unit in possible_units:
                    unit.no_passengers = 0
                
                for unit in possible_units:
                    while unit.no_passengers < people_per_unit:
                        passenger_id = indices.pop()
                        passenger = commuting_people[passenger_id]
                        unit.add(passenger,
                            activity = "commute",
                            subgroup_type=unit.SubgroupType.default,
                            )
                        #unit.no_passengers += 1

                while indices:
                    passenger_id = indices.pop()
                    passenger = commuting_people[passenger_id]
                    unit.add(passenger,
                            activity = "commute",
                            subgroup_type=unit.SubgroupType.default,
                            )
                    #unit.no_passengers += 1




       
