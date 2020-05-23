import numpy as np
from travelunit import TravelUnit, TravelUnits

class TravelUnitDistributor:
    """
    Distirbute people to other cities and back again if not active elsewhere

    Note: This distibutor is dynamic and so should be called at each travel time step to decide who
          is assigned to which units to determine mixing

    Assumptions:
    - People will travel to and from the same cities in a day if not active
    - In the return journey the only people travelling will be those who are returning from where they came
    """

    def __init__(self, travelcities, travelunits):
        """
        travelcities: (list) members of the TravelCities class
        travelunits: (list) members of the TravelUnits class
        """
        
        self.travelcities = travelcities
        self.travelunits = travelunits

    def from_file(self):

        self.to_distribute_df = 
        self.distribution_df = 

    def distribute_people_out(self):.
        'Distirbute people out in the day to other cities'

        # initialise new travelunits
        self.travelunits = []
        
        for travelcity in self.travelcities:
            to_distribute_global = self.to_distribute_df[travelcity.city]
            
            to_distirbute_per_city = to_distribute_global*np.array(self.distribution_df[travelcity.city])

            # where to draw people from overall
            travel_msoas = np.array(travelcity.msoas)
            
            for dest_city_idx, to_distribute in enumerate(to_distribute_per_city):

                # drawing people from specific msoas
                msoas = travel_msoas[np.random.choice(len(travel_msoas), len(to_distribute))]

                unique_msoas, counts = np.unique(msoas, return_counts = True)
                
                travel_unit = TravelUnit(
                    city = travelcity.city,
                )
                
                for msoa_idx, msoa in enumerate(unique_msoas):

                    people = np.array(msoa.people)[np.random.choice(len(msoa.people), counts[msoa_idx], replace=False)]
                    
                    for person in people:
                    
                        if len(travel_unit.no_passengers) < travel_unit.max_passengers:

                            person.home_city = travelcity.city
                            travel_unit.passengers.add(person)
                            travel_unit.no_passengers += 1
                            
                        else:
                            self.travelunits.append(travel_unit)

                            # seed new travel unit once other has been filled
                            travel_unit = TravelUnit(
                                city = travelcity.city,
                            )

                            person.home_city = travelcity.city
                            travel_unit.passengers.add(person)
                            travel_unit.no_passengers += 1

                        # send person to city
                        self.travelcities[dest_city_idx].arrived.append(person)

                # cleanup
                self.travelunits.append(travel_unit)
                
                
            


    def distribute_people_back(self):
        'If people are not active in another group (like hotels) then send them back home again'

        # initialise new travelunits
        self.travelunits = []

        units = []
        travel_cities = []
        for idx, travelcity in enumerate(self.travelcities):
            units.append(
                TravelUnit(
                    city = travelcity.city,
                )
            )
            travel_cities.append(travelcity.city)

        units = np.array(units)
        travel_city = np.array(travel_city)

        for travelcity_from in self.travelcities:

            to_distirbute = travelcity_from.arrived

            for person in to_distirbute:

                travel_city_index = np.where(travel_cities == person.home_city)[0]
                
                if len(units[travel_city_index].no_passengers) < units[travel_city_index].max_passengers:

                    units[travel_city_index].add(person)
                    travel_unit.no_passengers += 1

                else:

                    self.travelunits.append(units[travel_city_index])

                    # Create fresh unit in same location as previous one
                    units[travel_city_index] = TravelUnit(
                        city = travelcity.city
                    )

                    units[travel_city_index].add(person)
                    travel_unit.no_passengers += 1

        # clean up
        for unit in units:
            self.travelunits.append(unit)

                
