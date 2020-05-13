import numpy as np
from travelunit import TravelUnit, TravelUnits

class TravelUnitDistributor:

    def __init__(self, travelcities, travelunits, to_distribute_df, distribution_df, msoas):
        
        self.travelcities
        self.travelunits = travelunits
        self.to_distribute_df
        self.distribution_df = distribution_df
        self.msoas

    def distribute_people(self):

        ids = 0

        
        for travelcity in travelcities:
            to_distribute_global = self.to_distribute[travelcity.city]
            
            to_distirbute_per_city = to_distribute_global*np.array(self.distribution_df[travelcity.city])

            # where to draw people from overall
            travel_msoas = np.array(travelcity.msoas)
            
            for dest_city_idx, to_distribute in enumerate(to_distribute_per_city):

                # drawing people from specific msoas
                msoas = travel_msoas[np.random.choice(len(travel_msoas), len(to_distribute))]

                travel_unit = TravelUnit(
                    travelunit_id = ids,
                    city = travelcity.city,
                )
            
                for msoa in msoas:

                    if len(travel_unit.passengers) < travel_unit.max_passengers:

                        # get people who live in msoa
                        person = msoa.people[np.random.choice(len(msoa.people), 1)]
                        travel_unit.passengers.append(person)
                    
                    else:
                        travelunits.members.append(travel_unit)

                        # seed new travel unit once other has been filled
                        ids += 1
                        travel_unit = TravelUnit(
                            travelunit_id = ids,
                            city = travelcity.city,
                        )
                        person = msoa.people[np.random.choice(len(msoa.people), 1)]
                        travel_unit.passengers.append(person)

                # sent person to city
                self.travelcities[dest_city_idx].arrived.append(person)

            
