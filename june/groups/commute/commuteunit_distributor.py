import numpy as np
from random import shuffle

class CommuteUnitDistributor:
    """
    Distirbute people to commute units based on the hubs they are affiliated to

    Note: This distibutor is dynamic and so should be called at each commutng time step to decide who
          is assigned to which units to determine mixing
    """    

    def __init__(self, commutehubs):
        """
        commutehubs: (list) members of CommuteHubs
        """
        self.commutehubs = commutehubs

    def distribute_people(self):
        for hub in self.commutehubs:
            if hub.people:
                possible_units = hub.commuteunits
                commuting_people = hub.people
                indices = list(range(len(commuting_people)))
                shuffle(indices)
                people_per_unit = len(commuting_people)//len(possible_units)
                # clear units
                for unit in possible_units:
                    unit.no_passengers = 0

                for unit in possible_units:
                    while unit.no_passengers < people_per_unit:
                        passenger_id = indices.pop()
                        passenger = commuting_people[passenger_id]
                        unit.add(passenger,
                            activity="commute",
                            subgroup_type=unit.SubgroupType.default,
                            dynamic=True
                            )
                        unit.no_passengers += 1

                while indices:
                    passenger_id = indices.pop()
                    passenger = commuting_people[passenger_id]
                    unit.add(passenger,
                            activity= "commute",
                            subgroup_type=unit.SubgroupType.default,
                            dynamic=True
                            )
                    unit.no_passengers += 1



