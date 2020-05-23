import numpy as np
from travelunit import TravelUnit, TravelUnits

class TravelUnitDistributor:
    """
    Distirbute people to other cities and back again if not active elsewhere

    Assumptions:
    - People will travel to and from the same cities in a day if not active
    - In the return journey the only people travelling will be those who are returning from where they came
    """

    def __init__(self, travelcities, travelunits, msoas):
        """
        
        """
        
        self.travelcities = travelcities
        self.travelunits = travelunits
        self.msoas = mspas

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

                travel_unit = TravelUnit(
                    city = travelcity.city,
                )
            
                for msoa in msoas:

                    if len(travel_unit.no_passengers) < travel_unit.max_passengers:

                        # get people who live in msoa
                        person = msoa.people[np.random.choice(len(msoa.people), 1)]
                        travel_unit.passengers.add(person)
                        travel_unit.no_passengers += 1
                    
                    else:
                        self.travelunits.append(travel_unit)

                        # seed new travel unit once other has been filled
                        travel_unit = TravelUnit(
                            city = travelcity.city,
                        )
                        person = msoa.people[np.random.choice(len(msoa.people), 1)]
                        person.home_city = travelcity
                        travel_unit.passengers.add(person)
                        travel_unit.no_passengers += 1


                self.travelunits.append(travel_unit)
                # sent person to city
                self.travelcities[dest_city_idx].arrived.append(person)
            


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

            # TODO: check if not active

            for person in to_distirbute:

                travel_city_index = np.where(travel_cities == person.home_city)[0]
                
                if len(units[travel_city_index].no_passengers) < units[travel_city_index].max_passengers:

                    units[travel_city_index].passengers.add(person)
                    travel_unit.no_passengers += 1

                else:

                    self.travelunits.append(units[travel_city_index])

                    ids += 1
                    units[travel_city_index] = TravelUnit(
                        city = travelcity.city
                    )

                    units[travel_city_index].passengers.add(person)
                    travel_unit.no_passengers += 1

        # assign hanging units
        for unit in units:
            self.travelunits.append(unit)

                
