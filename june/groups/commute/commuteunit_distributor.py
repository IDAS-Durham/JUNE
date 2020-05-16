import numpy as np

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

            possible_units = hub.commuteunits
            to_commute = hub.people

            # loop over all passengers who need to commute
            for passenger in to_commute:

                # assign passengers to commute units
                assigned = False
                while assigned == False:
                
                    unit_choice = np.random.randint(len(possible_units))
                    unit = possible_units[unit_choice]
                    
                    if unit.no_passengers < unit.max_passengers:
                        unit.passengers.add(passenger)
                        unit.no_passengers += 1
                        assigned = True
                        # make this more efficient by stopping looking at things already filled
                    else:
                        pass
        
