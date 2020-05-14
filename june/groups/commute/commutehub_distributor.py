import csv
from june import config
from scipy import spatial

default_geographical_data_directory = f"{config.data_path}/geographical_data"
default_travel_data_directory = f"{config.data_path}/travel"

default_file = f"{default_geographical_data_directory}/msoa_oa.csv"


class CommuteHubDistributor:
    """
    Distribute people to commute hubs based on where they live and where they are commuting to
    """

    def __init__(self, coordinates_dict: dict, commutecities: list):
        """
        Parameters
        ----------
        coordinates_dict
            dictionary of all OA postcodes and lat/lon coordinates and their equivalent MSOA
        commutecities
            members of CommuteCities
        """
        self.coordinates_dict = coordinates_dict
        self.commutecities = commutecities

    @classmethod
    def from_file(
            cls,
            commute_cities: list,
            msoa_os_coordinates_file: str = default_file
    ) -> "CommuteHubDistributor":
        """
        Load OA postcode data from a CSV and construct
        a dictionary for fast lookup

        Parameters
        ----------
        commute_cities
        msoa_os_coordinates_file

        Returns
        -------
        A distributor
        """
        coordinates_dict = dict()
        with open(msoa_os_coordinates_file) as f:
            reader = csv.reader(f)
            headers = next(reader)
            key_index = headers.index("OA11CD")
            for row in reader:
                row_dict = dict(zip(
                    headers,
                    row
                ))
                row_dict["X"] = float(row_dict["X"])
                row_dict["Y"] = float(row_dict["Y"])
                coordinates_dict[row[key_index]] = row_dict
        return CommuteHubDistributor(
            coordinates_dict=coordinates_dict,
            commutecities=commute_cities
        )

    def _get_msoa_oa(self, oa):
        'Get MSOA for a give OA'
        return self.coordinates_dict[
            oa
        ]["MSOA11CD"]

    def _get_area_lat_lon(self, oa):
        'Get lat/lon for  a given OA'
        area_dict = self.coordinates_dict[
            oa
        ]

        return area_dict["Y"], area_dict["X"]

    def distribute_people(self):

        for commutecity in self.commutecities:
            # people commuting into city
            work_people = commutecity.passengers

            # THIS IS GLACIALLY SLOW
            to_commute_in = []
            to_commute_out = []
            for work_person in work_people:
                msoa = self._get_msoa_oa(work_person.area.name)
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
