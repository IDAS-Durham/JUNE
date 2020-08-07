import logging
import os
from enum import IntEnum
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import yaml
from june.groups.travel.travelunit import TravelUnit, TravelUnits

from june import paths

default_config_filename = paths.configs_path / "defaults/rail_travel.yaml"

default_data_path = paths.data_path

default_to_distirbute = default_data_path / "input/travel/rail_travel_no_commute.csv"

default_distribution = default_data_path / "input/travel/rail_travel_distribution.csv"



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

    def from_file(self, \
                  to_distribute = default_to_distirbute, \
                  distribution = default_distribution, \
                  config_filename = default_config_filename
    ):

        self.to_distribute_df = pd.read_csv(to_distribute)
        self.distribution_df = pd.read_csv(distribution)

        with open(config_filename) as f:
            self.configs = yaml.load(f, Loader=yaml.FullLoader)

    def distribute_people_out(self):
        'Distirbute people out in the day to other cities'

        # initialise new travelunits
        self.travelunits.clear()

        # Clear arrived list
        # Note: this may need to be diabled for oevrnight stays
        for travelcity in self.travelcities:
            travelcity.arrived.clear()
        
        for idx, travelcity in enumerate(self.travelcities):
            if travelcity.city == 'London':
                to_distribute_global = list(self.to_distribute_df[self.to_distribute_df['station'] == travelcity.city]['average_no_commute'])[0]*(1-self.configs['London damping factor'])
            else:
                to_distribute_global = list(self.to_distribute_df[self.to_distribute_df['station'] == travelcity.city]['average_no_commute'])[0]*(1-self.configs['non-London damping factor'])

            
            to_distribute_per_city = to_distribute_global*np.array(self.distribution_df[travelcity.city])

            # where to draw people from overall
            travel_msoas = np.array(travelcity.msoas)

            for dest_city_idx, to_distribute in enumerate(to_distribute_per_city):

                # drawing people from specific msoas
                if not travel_msoas.size:
                    msoas = []
                else:
                    msoas = travel_msoas[np.random.choice(len(travel_msoas), int(to_distribute))]

                msoa_names = []
                for msoa in msoas:
                    msoa_names.append(msoa.name)
                msoa_names = np.array(msoa_names)

                unique_msoa_names, counts = np.unique(msoa_names, return_counts = True)

                
                travel_unit = TravelUnit(
                    city = travelcity.city,
                )
                
                for msoa_idx, msoa_name in enumerate(unique_msoa_names):
                    
                    msoa = msoas[np.where(msoa_names == msoa_name)[0][0]]

                    people = np.array(msoa.people)[np.random.choice(len(msoa.people), counts[msoa_idx], replace=False)]
                    
                    for person in people:
                    
                        if travel_unit.no_passengers < travel_unit.max_passengers:

                            person.home_city = travelcity.city
                            travel_unit.add(person,
                                            activity="rail_travel",
                                            subgroup_type=travel_unit.SubgroupType.default,
                                            dynamic=True
                            )
                            travel_unit.no_passengers += 1

                            
                        else:
                            #assert len(travel_unit.people) == travel_unit.no_passengers
                            self.travelunits.append(travel_unit)

                            # seed new travel unit once other has been filled
                            travel_unit = TravelUnit(
                                city = travelcity.city,
                            )

                            person.home_city = travelcity.city
                            travel_unit.add(person,
                                            activity="rail_travel",
                                            subgroup_type=travel_unit.SubgroupType.default,
                                            dynamic=True
                            )
                            travel_unit.no_passengers += 1

                        # send person to city
                        self.travelcities[dest_city_idx].arrived.append(person)

                # cleanup
                self.travelunits.append(travel_unit)

    def distribute_people_back(self):
        'If people are not active in another group (like hotels) then send them back home again'

        # initialise new travelunits
        self.travelunits.clear()

        units = []
        travel_cities = []
        for idx, travelcity in enumerate(self.travelcities):
            units.append(
                TravelUnit(
                    city = travelcity.city,
                )
            )
            travel_cities.append(travelcity.city)

        #units = np.array(units)
        travel_cities = np.array(travel_cities)

        for travelcity_from in self.travelcities:

            to_distirbute = travelcity_from.arrived

            for person in to_distirbute:

                travel_city_index = np.where(travel_cities == person.home_city)[0][0]

                travel_unit = units[travel_city_index]
                
                if travel_unit.no_passengers < travel_unit.max_passengers:

                    travel_unit.add(person,
                                    activity="rail_travel",
                                    subgroup_type=travel_unit.SubgroupType.default,
                                    dynamic=True
                    )
                    travel_unit.no_passengers += 1

                else:

                    self.travelunits.append(travel_unit)

                    # Create fresh unit in same location as previous one
                    travel_unit = TravelUnit(
                        city = travelcity.city
                    )

                    units[travel_city_index] = travel_unit

                    travel_unit.add(person,
                                    activity="rail_travel",
                                    subgroup_type=travel_unit.SubgroupType.default,
                                    dynamic=True
                    )
                    travel_unit.no_passengers += 1

        # clean up
        for unit in units:
            self.travelunits.append(unit)

                
