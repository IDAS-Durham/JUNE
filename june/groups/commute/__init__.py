from june import paths

import pandas as pd

from .commutecity import CommuteCity, CommuteCities
from .commutecity_distributor import CommuteCityDistributor
from .commutecityunit import CommuteCityUnit, CommuteCityUnits
from .commutecityunit_distributor import CommuteCityUnitDistributor
from .commutehub import CommuteHub, CommuteHubs
from .commutehub_distributor import CommuteHubDistributor
from .commuteunit import CommuteUnit, CommuteUnits
from .commuteunit_distributor import CommuteUnitDistributor

data_directory = paths.data_path
default_geographical_data_directory = data_directory / "geographical_data"
default_travel_data_directory = data_directory / "travel"


# class Commute:
#     @classmethod
#     def from_directories(
#             cls,
#             super_areas,
#             geographical_data_directory=default_geographical_data_directory,
#             travel_data_directory=default_travel_data_directory
#     ):
#         uk_pcs_coordinates = pd.read_csv(
#             f"{geographical_data_directory}/ukpostcodes_coordinates.csv"
#         )
#         msoa_coordinates = pd.read_csv(
#             f"{geographical_data_directory}/msoa_coordinates_englandwales.csv"
#         )
#         msoa_oa_coordinates_filename = f"{geographical_data_directory}/msoa_oa.csv"

#         london_stat_pcs = pd.read_csv(
#             f"{travel_data_directory}/London_station_coordinates.csv"
#         )
#         non_london_stat_pcs = pd.read_csv(
#             f"{travel_data_directory}/non_London_station_coordinates.csv"
#         )
#         return Commute(
#             super_areas,
#             uk_pcs_coordinates,
#             msoa_coordinates,
#             msoa_oa_coordinates_filename,
#             london_stat_pcs,
#             non_london_stat_pcs
#         )

#     def __init__(
#             self,
#             super_areas,
#             uk_pcs_coordinates,
#             msoa_coordinates,
#             msoa_oa_coordinates_filename,
#             london_stat_pcs,
#             non_london_stat_pcs
#     ):
#         """
#         Populates the world with stations and commtute hubs and distibutes people accordingly
#         """
#         print("Initializing commute...")
#         # CommuteCity
#         commutecities = CommuteCities(uk_pcs_coordinates, msoa_coordinates)
#         # Crucial that London is initialise second, after non-London
#         commutecities.init_non_london(non_london_stat_pcs)
#         commutecities.init_london(london_stat_pcs)

#         commutecity_distributor = CommuteCityDistributor(commutecities.members, super_areas.members)
#         commutecity_distributor.distribute_people()

#         # CommuteHub
#         commutehubs = CommuteHubs(commutecities.members, msoa_coordinates, init=True)

#         commutehub_distributor = CommuteHubDistributor.from_file(
#             msoa_oa_coordinates_filename,
#             commutecities.members
#         )
#         commutehub_distributor.distribute_people()

#         # CommuteUnit
#         self.commuteunits = CommuteUnits(commutehubs.members, init=True)

#         self.commuteunit_distributor = CommuteUnitDistributor(commutehubs.members)
#         # unit distirbutor is dynamic and should be called at each time step - leave this until later
#         # commuteunit_distributor.distribute_people()

#         # CommuteCityUnit
#         self.commutecityunits = CommuteCityUnits(commutecities.members, init=True)
#         # unit distirbutor is dynamic and should be called at each time step - leave this until later
#         # commutecityunit_distributor = CommuteCityUnitDistributor(commutecities.members)
