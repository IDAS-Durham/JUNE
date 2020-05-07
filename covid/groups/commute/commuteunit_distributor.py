import numpy as np

class CommuteUnitDistributor:

    def __init__(self, commuteunits, commutehubs):
        self.commuteunits = commuteunits
        self.commutehubs = commutehubs

    def distribute_people(self):

        for hub in self.commutehub:

            possible_units = hub.commuteunits
            to_commute = hub.passengers
            
            unit_choice = np.random.choice(
                
            )
            # make people commute
        
