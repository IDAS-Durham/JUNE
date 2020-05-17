import numpy as np

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

            # Clear all units of passengers before running
            possible_units = city.commutecityunits
            for unit in possible_units:
                unit.passengers = 0
            
            to_commute = city.commute_internal

            # loop over all passengers who need to commute
            for passenger in to_commute:

                # assign passengers to commute units
                assigned = False
                while not assigned:
                
                    unit_choice = np.random.randint(len(possible_units))
                    unit = possible_units[unit_choice]
                    
                    if unit.no_passengers < unit.max_passengers:
                        unit.add(passenger,
                                activity_type=passenger.ActivityType.commute,
                                subgroup_type=unit.SubgroupType.default)
                        unit.no_passengers += 1
                        assigned = True
                        # make this more efficient by stopping looking at things already filled
                    else:
                        pass
        
