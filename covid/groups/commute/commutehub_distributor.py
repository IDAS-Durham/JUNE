import numpy as np
from scipy import spatial


class CommuteHubDistributor:

    def __init__(self, oa_coordinates, commutecities, commutehubs):
        self.oa_coordinates = oa_coordinates
        self.commutecities = commutecities
        self.commutehubs = commutehubs

    def _get_area_lat_lon(self, oa):
        lat = float(self.oa_coordinates['Y'][self.oa_coordinates['OA11CD'] == oa])
        lon = float(self.oa_coordinates['X'][self.oa_coordinates['OA11CD'] == oa])

        return [lat,lon]

    def distirbute_people(self):

        for commutecity in self.commutecities:
            # people commuting into city
            work_people = commutecity.passengers

            commutehub_in_city = []
            commutehub_in_city_lat_lon = []
            for commutehub in self.commutehubs:
                if commutehub.city == commutecity.city:
                    commutehub_in_city.append(commutehub)
                    commutehub_in_city_lat_lon.append(commutehub.lat_lon)

            for work_person in work_people:
                # check if live AND work in metropolitan area
                if work_person.msoarea in commutecity.metro_msoas:
                    pass

                # if they live outside and commute in then they need to commute through a hub
                else:
                    live_area = work_person.area
                    live_lat_lon = self._get_area_lat_lon(live_area)
                    _, hub_index = spatial.KDTree(commutehub_in_city).query(live_lat_lon,1)

                    commutehub_in_city[hub_index].passengers.append(work_person)
                    
                    
                    
