import numpy as np

class CommuteUnit:
    """
    Defines commute unites (e.g. train carriages) which people commute in and interact
    These units will be filled dynamically
    """

    def __init__(self, commuteunit_id, city, commutehub_id):
        """
        id: (int) id of the commute unit
        station: (string) name of the city the commute unt is associated to
        commutehub_id: (int) id of commute hub unit is associated to
        passengers: (list) passengers commuting in the commute unit
        no_passenders: (int) counter of the number of passengers currently in the commute unit
        max_passengers: (int) capacity of the commute unit

        Note: Overcrowding will be accounted for in the interaction model
              i.e. the just because the number of passengers in the unit <= 50 does not mean there
                   is no overcrowding
        """
        self.id = commuteunit_id
        self.city = city
        self.commutehub_id = commutehub_id
        self.passengers = []
        self.no_passengers = 0
        self.max_passengers = 50 # assume all units are of equal size but this could be made more granular later

class CommuteUnits:
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

    def __init__(self, commutehubs, init = False):
        """
        commutehubs: (list) members of CommuteHubs
        init: (bool) if True, initialise units, if False do this manually
        members: (list) list of all commute units
        """
        self.commutehubs = commutehubs
        self.init = init
        self.members = []

        if self.init:
            self.init_units()

    def init_units(self):
        'Initialise units'

        ids = 0
        for hub in self.commutehubs:
            no_passengers = len(hub.passengers)
            no_units = int(float(no_passengers)/50) + 1

            for i in range(no_units):
                commute_unit = CommuteUnit(
                    commuteunit_id = ids,
                    city = hub.city,
                    commutehub_id = hub.id
                )

                self.members.append(commute_unit)
                hub.commuteunits.append(commute_unit)
                
            ids += 1
            
        
