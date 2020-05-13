from scipy import spatial


class CommuteHubDistributor:
    """
    Distribute people to commute hubs based on where they live and where they are commuting to
    """

    def __init__(self, msoa_oa_coordinates, commutecities):
        """
        msoa_oa_coordinates: (pd.Dataframe) Dataframe of all OA postcodes and lat/lon coordinates and their equivalent MSOA
        commutecities: (list) members of CommuteCities
        """
        self.msoa_oa_coordinates = msoa_oa_coordinates
        self.commutecities = commutecities

    def _get_msoa_oa(self, oa):
        'Get MSOA for a give OA'

        msoa = self.msoa_oa_coordinates['MSOA11CD'][self.msoa_oa_coordinates['OA11CD'] == oa]

        return msoa

    def _get_area_lat_lon(self, oa):
        'Get lat/lon for  a given OA'
        lat = float(self.msoa_oa_coordinates['Y'][self.msoa_oa_coordinates['OA11CD'] == oa])
        lon = float(self.msoa_oa_coordinates['X'][self.msoa_oa_coordinates['OA11CD'] == oa])

        return [lat, lon]

    def distribute_people(self):

        for commutecity in self.commutecities:
            # people commuting into city
            work_people = commutecity.passengers

            # THIS IS GLACIALLY SLOW
            to_commute_in = []
            to_commute_out = []
            for work_person in work_people:
                msoa = list(self._get_msoa_oa(work_person.area.name))[0]
                # check if live AND work in metropolitan area
                if msoa in commutecity.metro_msoas:
                    to_commute_in.append(work_person)
                # if they live outside and commute in then they need to commute through a hub
                else:
                    to_commute_out.append(work_person)

            # possible commutehubs
            commutehub_in_city = commutecity.commutehubs
            commutehub_in_city_lat_lon = []
            for commutehub in commutehub_in_city:
                commutehub_in_city_lat_lon.append(commutehub.lat_lon)

            commutehub_tree = spatial.KDTree(commutehub_in_city_lat_lon)

            # THIS IS GLACIALLY SLOW
            for work_person in to_commute_out:
                live_area = work_person.area.name
                live_lat_lon = self._get_area_lat_lon(live_area)
                # find nearest commute hub to the person given where they live
                _, hub_index = commutehub_tree.query(live_lat_lon, 1)

                commutehub_in_city[hub_index].passengers.append(work_person)

            for work_person in to_commute_in:
                commutecity.commute_internal.append(work_person)
