import numpy as np

class TravelUnitDistributor:

    def __init__(self, travelcities, travelunits, to_distribute_df, distribution_df):

        self.travelcities
        self.travelunits = travelunits
        self.to_distribute_df
        self.distribution_df = distribution_df

    def distribute_people(self):

        for travelcity in travelcities:
            to_distribute = self.to_distribute[travelcity.city]

            msoas = np.choice(len(travelcity.msoas), len(to_distribute))
            for msoa in msoas:
                #select people
    
