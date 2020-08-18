from june.groups.group import Group, Supergroup

import numpy as np

class CommuteUnit(Group):
    """
    Defines commute unites (e.g. train carriages) which people commute in and interact
    These units will be filled dynamically
    """

    def __init__(self, city, commutehub_id, is_peak):
        """
        city: (string) name of the city the commute unt is associated to
        commutehub_id: (int) id of commute hub unit is associated to
        people: (Group structure) passengers commuting in the commute unit
        no_passenders: (int) counter of the number of passengers currently in the commute unit
        max_passengers: (int) capacity of the commute unit
        is_peak: (bool) if True, unit travels at peak time, else it does not

        Note: Overcrowding will be accounted for in the interaction model
              i.e. the just because the number of passengers in the unit <= 50 does not mean there
                   is no overcrowding
        """
        super().__init__()
        
        self.city = city
        self.commutehub_id = commutehub_id
        self.no_passengers = 0
        self.max_passengers = 50 # assume all units are of equal size but this could be made more granular later
        self.is_peak = is_peak

class CommuteUnits(Supergroup):
    """
    Initialise commute units given the commute hubs they are affilited to

    Assumptions:
    - The number of units assigned to a hub is equal to the number of passengers who are commuting through
      that hub divided by 50 (the currently fixed size of the commute units) + 1 (to account for no overfilling)
    - This first assumption means that each unit is almost completely filled on average
      While this may be a good assumption given crowded commuter transport systems - it may also not matter too much
      since only a subset of people interact in each unit (although the intensity may well be increased give crowing)
      - Adjusting this could be a later improvement of the code
    """

    def __init__(self, commutehubs, init=False):
        """
        commutehubs: (list) members of CommuteHubs
        init: (bool) if True, initialise units, if False do this manually
        members: (list) list of all commute units
        """
        super().__init__()

        self.commutehubs = commutehubs
        self.init = init
        self.members = []

        
    def init_units(self):
        'Initialise units'

        ids = 0
        for hub in self.commutehubs:
            no_passengers = len(hub.people)
            no_units = int(float(no_passengers)/50) + 1
            # assign unit to peak/not peak times with prob 0.8/0.2
            # make this a parameter in the future
            peak_not_peak = np.random.choice(2,no_units,[0.8,0.2])
            
            for i in range(no_units):
                commute_unit = CommuteUnit(
                    #commuteunit_id = ids,
                    city = hub.city,
                    commutehub_id = hub.id,
                    is_peak = peak_not_peak[i]
                )

                self.members.append(commute_unit)
                hub.commuteunits.append(commute_unit)
                
            ids += 1
            
        
