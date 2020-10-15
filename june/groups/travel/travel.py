import logging
import yaml
from random import randint
from typing import List
from enum import IntEnum
from itertools import chain
import numpy as np
from collections import defaultdict

logger = logging.getLogger("travel")

from june.paths import configs_path, data_path
from june.geography import Cities, Stations, Station
from june.groups import Group, Supergroup
from june.world import World
from .transport import (
    Transport,
    Transports,
    CityTransport,
    CityTransports,
    InterCityTransport,
    InterCityTransports,
)
from .mode_of_transport import ModeOfTransport, ModeOfTransportGenerator

default_cities_filename = data_path / "input/geography/cities_per_super_area_ew.csv"

default_city_stations_config_filename = (
    configs_path / "defaults/travel/city_stations.yaml"
)

default_commute_config_filename = configs_path / "defaults/groups/travel/commute.yaml"


class Travel:
    """
    This class handles all functionality related to travel, from local commute,
    to inter-city and inter-regional travel.
    """

    def __init__(
        self,
        city_super_areas_filename=default_cities_filename,
        city_stations_filename=default_city_stations_config_filename,
        commute_config_filename=default_commute_config_filename,
    ):
        self.city_super_areas_filename = city_super_areas_filename
        self.city_stations_filename = city_stations_filename
        with open(commute_config_filename) as f:
            self.commute_config = yaml.load(f, Loader=yaml.FullLoader)

    def initialise_commute(
        self, world: World, maximum_number_commuters_per_city_station=200000
    ):
        logger.info(f"Initialising commute...")
        self._generate_cities(
            world=world, city_super_areas_filename=self.city_super_areas_filename,
        )
        self._assign_mode_of_transport_to_people(world=world)
        commuters_dict = self._get_city_commuters(
            world=world, city_stations_filename=self.city_stations_filename
        )
        self._create_stations(
            world=world,
            commuters_dict=commuters_dict,
            maximum_number_commuters_per_city_station=maximum_number_commuters_per_city_station,
            city_stations_filename=self.city_stations_filename,
        )
        self._distribute_commuters_to_stations(
            world=world, commuters_dict=commuters_dict,
        )
        self._create_transports_in_cities(world)

    def get_commute_subgroup(self, person):
        work_city = person.work_city
        if work_city is None or not person.mode_of_transport.is_public:
            return
        subgroup = work_city.get_commute_subgroup(person)
        person.subgroups.commute = subgroup
        return subgroup

    def _generate_cities(self, world, city_super_areas_filename: str):
        """
        Generates cities in the current world.
        """
        # initialise cities
        logger.info("Creating cities...")
        world.cities = Cities.for_super_areas(
            world.super_areas, city_super_areas_filename=city_super_areas_filename
        )
        city_names = [city.name for city in world.cities]
        if len(city_names) > 0:
            logger.info(
                f"This world has {len(city_names)} cities, with names\n" f"{city_names}"
            )
        else:
            logger.info(f"This world has no important cities in it")

    def _assign_mode_of_transport_to_people(self, world: World):
        """
        Assigns a mode of transport (public or not) to the world's population.
        """
        logger.info(f"Determining people mode of transport")
        mode_of_transport_generator = ModeOfTransportGenerator.from_file()
        for i, area in enumerate(world.areas):
            if i % 4000 == 0:
                logger.info(
                    f"Mode of transport allocated in {i} of {len(world.areas)} areas."
                )
            mode_of_transport_generator_area = mode_of_transport_generator.regional_gen_from_area(
                area.name
            )
            for person in area.people:
                if person.age < 18 or person.age >= 65:
                    person.mode_of_transport = ModeOfTransport(
                        description="Not in employment", is_public=False
                    )
                else:
                    person.mode_of_transport = (
                        mode_of_transport_generator_area.weighted_random_choice()
                    )
        logger.info(f"Mode of transport determined for everyone.")

    def _get_city_commuters(self, world: World, city_stations_filename: str):
        """
        Gets internal and external commuters per city.
        - If the person lives and works in the same city, then the person is assigned 
          to be an internal commuter (think as the person takes the subway).
        - If the person lives outside their working city, then that person has to commute
          through a station, and is assigned to the city external commuters.
        - Likewise for the people living in the city but working outside.

        """
        with open(city_stations_filename) as f:
            cities_with_stations = yaml.load(f, Loader=yaml.FullLoader)[
                "number_of_inter_city_stations"
            ]
        ret = {}
        for city in world.cities:
            if city.name in cities_with_stations:
                ret[city.name] = {"internal": [], "external": []}
        logger.info(f"Assigning commuters to stations...")
        for i, person in enumerate(world.people):
            if person.mode_of_transport.is_public:
                if (
                    person.work_city is not None
                    and person.work_city.name in cities_with_stations
                ):
                    if person.home_city == person.work_city:
                        # this person commutes internally
                        ret[person.work_city.name]["internal"].append(person.id)
                    else:
                        # commutes away to an external station
                        ret[person.work_city.name]["external"].append(person.id)
            if i % 500_000 == 0:
                logger.info(
                    f"Assigned {i} of {len(world.people)} potential commuters..."
                )
        logger.info(f"Commuters assigned")
        for key, value in ret.items():
            internal = value["internal"]
            external = value["external"]
            if len(internal) + len(external) > 0:
                logger.info(
                    f"City {key} has {len(internal)} internal and {len(external)} external commuters."
                )
        return ret

    def _create_stations(
        self,
        world: World,
        city_stations_filename: str,
        commuters_dict: dict,
        maximum_number_commuters_per_city_station: int,
    ):
        """
        Generates cities, super stations, and stations on the given world.
        """
        with open(city_stations_filename) as f:
            inter_city_stations_per_city = yaml.load(f, Loader=yaml.FullLoader)[
                "number_of_inter_city_stations"
            ]
        logger.info("Creating stations...")
        world.stations = Stations([])
        for city in world.cities:
            if city.name not in inter_city_stations_per_city:
                continue
            else:
                n_inter_city_stations = inter_city_stations_per_city[city.name]
                city.inter_city_stations = Stations.from_city_center(
                    city=city,
                    super_areas=world.super_areas,
                    number_of_stations=n_inter_city_stations,
                    type="inter_city_station",
                    distance_to_city_center=10,
                )
                city.inter_city_stations._construct_ball_tree()
                world.stations += city.inter_city_stations
                n_internal_commuters = len(commuters_dict[city.name]["internal"])
                n_city_stations = int(
                    np.ceil(
                        n_internal_commuters / maximum_number_commuters_per_city_station
                    )
                )
                city.city_stations = Stations.from_city_center(
                    city=city,
                    super_areas=world.super_areas,
                    number_of_stations=n_city_stations,
                    type="city_station",
                    distance_to_city_center=5,
                )
                city.city_stations._construct_ball_tree()
                world.stations += city.city_stations
                # initialise ball tree for stations in the city.
                logger.info(
                    f"City {city.name} has {n_city_stations} city "
                    f"and {n_inter_city_stations} inter city stations."
                )
        for super_area in world.super_areas:
            for city in world.cities:
                if city.has_stations:
                    super_area.closest_inter_city_station_for_city[
                        city.name
                    ] = city.get_closest_inter_city_station(super_area.coordinates)

    def _distribute_commuters_to_stations(self, world: World, commuters_dict: dict):
        for city, commuters in commuters_dict.items():
            city = world.cities.get_by_name(city)
            city.internal_commuter_ids = set(commuters["internal"])
            for external_commuter_id in commuters["external"]:
                external_commuter = world.people.get_from_id(external_commuter_id)
                work_city = external_commuter.work_city.name
                station = external_commuter.super_area.closest_inter_city_station_for_city[
                    work_city
                ]
                station.commuter_ids.add(external_commuter_id)

    def _create_transports_in_cities(
        self, world, seats_per_city_transport=50, seats_per_inter_city_transport=50
    ):
        """
        Creates city transports and inter city transports in CityStations and
        InterCityStations respectively.
        """
        logger.info(f"Creating transport units for the population")
        world.city_transports = CityTransports([])
        world.inter_city_transports = InterCityTransports([])
        for city in world.cities:
            if city.has_stations:
                seats_per_passenger = self.commute_config["seats_per_passenger"].get(
                    city.name, 1
                )
                n_commute_internal = len(city.internal_commuter_ids)
                number_city_transports = int(
                    np.ceil(
                        (
                            seats_per_passenger
                            * n_commute_internal
                            / seats_per_city_transport
                        )
                    )
                )
                logger.info(
                    f"City {city.name} has {number_city_transports} city train carriages."
                )
                n_city_stations = len(city.city_stations)
                transports_per_station = int(
                    np.ceil(number_city_transports / n_city_stations)
                )
                for station in city.city_stations:
                    for _ in range(transports_per_station):
                        city_transport = CityTransport(station=station)
                        station.city_transports.append(city_transport)
                        world.city_transports.add(city_transport)
                        number_city_transports -= 1
                        if number_city_transports <= 0:
                            break
                number_inter_city_transports_total = 0
                for station in city.inter_city_stations:
                    if len(station.commuter_ids) == 0:
                        continue
                    number_inter_city_transports = int(
                        np.ceil(
                            (
                                seats_per_passenger
                                * len(station.commuter_ids)
                                / seats_per_inter_city_transport
                            )
                        )
                    )
                    number_inter_city_transports_total += number_inter_city_transports
                    for _ in range(number_inter_city_transports):
                        inter_city_transport = InterCityTransport(station=station)
                        station.inter_city_transports.append(inter_city_transport)
                        world.inter_city_transports.add(inter_city_transport)
                logger.info(
                    f"City {city.name} has {number_inter_city_transports_total} inter-city train carriages."
                )
        logger.info(f"Cities' transport initialised")
