import numpy as np
import random

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

    def chose_unit(self, possible_units):
        unit_choice = np.random.randint(len(possible_units))
        return possible_units[unit_choice]

    def distribute_people(self):

        for hub in self.commutehubs:
            if len(hub.people) > 0:
                possible_units = hub.commuteunits
                to_commute = hub.people
                indices = np.arange(len(to_commute))
                random.shuffle(indices)
                for unit in possible_units:
                    if len(to_commute) == 0:
                        break
                    while unit.no_passengers < unit.max_passengers and len(to_commute) > 0:
                        passenger_id = indices.pop()
                        passenger = to_commute[passenger_id]
                        unit.add(passenger,
                            activity_type=passenger.ActivityType.commute,
                            subgroup_type=unit.SubgroupType.default
                            )
                    unit.no_passengers += 1


