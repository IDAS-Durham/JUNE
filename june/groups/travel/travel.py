import logging
import yaml
from random import randint
from typing import List
from enum import IntEnum
from itertools import chain
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

from june.paths import configs_path, data_path
from june.geography import Cities, Stations, Station
from june.groups import Group, Supergroup
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


def generate_commuting_network(
    world,
    city_super_areas_filename=default_cities_filename,
    city_stations_filename=default_city_stations_config_filename,
):
    """
    Generates cities, super stations, and stations on the given world.
    """
    with open(city_stations_filename) as f:
        stations_per_city = yaml.load(f, Loader=yaml.FullLoader)["number_of_stations"]
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
    logger.info("Creating stations...")
    world.stations = Stations([])
    for city in world.cities:
        if city.name not in stations_per_city:
            continue
        else:
            n_stations = stations_per_city[city.name]
            city.stations = Stations.from_city_center(
                city=city, super_areas=world.super_areas, number_of_stations=n_stations
            )
            world.stations += city.stations
            # initialise ball tree for stations in the city.
            city.stations._construct_ball_tree()
            logger.info(f"City {city.name} has {n_stations} stations.")
    logger.info(f"This world has {len(world.stations)} stations.")
    logger.info(f"Recording closest stations to super areas")
    for super_area in world.super_areas:
        for city in world.cities:
            if city.has_stations:
                super_area.closest_station_for_city[
                    city.name
                ] = city.get_closest_station(super_area.coordinates)


class Travel:
    """
    This class handles all functionality related to travel, from local commute,
    to inter-city and inter-regional travel.
    """

    def __init__(
        self,
        city_super_areas_filename=default_cities_filename,
        city_stations_filename=default_city_stations_config_filename,
    ):
        self.city_super_areas_filename = city_super_areas_filename
        self.city_stations_filename = city_stations_filename

    def initialise_commute(self, world):
        logger.info(f"Initialising commute...")
        generate_commuting_network(
            world=world,
            city_super_areas_filename=self.city_super_areas_filename,
            city_stations_filename=self.city_stations_filename,
        )
        self.assign_mode_of_transport_to_people(world)
        self.distribute_commuters_to_stations_and_cities(world)
        self.create_transport_units_at_stations_and_cities(world)

    def assign_mode_of_transport_to_people(self, world):
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

    def distribute_commuters_to_stations_and_cities(self, world):
        """
        Distributes commuters to cities and stations. 
        - If the person lives and works in the same city, then the person is assigned to be an internal commuter (think as the person takes the subway).
        - If the person lives outside their working city, then that person has to commute through a station, and is assigned to the city external commuters.
        - Likewise for the people living in the city but working outside.

        Parameters
        ----------
        world
            an instance of World
        people_per_city_transport
            Maximum number of people inside a city transport.
        people_per_inter_city_transport
            Maximum number of people inside an inter city transport.
        """
        has_cities = world.cities is not None and len(world.cities) > 0
        has_stations = world.stations is not None and len(world.stations) > 0
        if not has_cities and not has_stations:
            logger.warning(f"No stations and cities in this world, no commuting.")
            return
        logger.info(f"Assigning commuters to stations...")
        for i, person in enumerate(world.people):
            if person.mode_of_transport.is_public:
                if person.work_city is not None and person.work_city.has_stations:
                    if person.home_city == person.work_city:
                        # this person commutes internally
                        person.work_city.commuter_ids.add(person.id)
                    elif world.stations:
                        # commutes away to an external station
                        person.super_area.closest_station_for_city[
                            person.work_city.name
                        ].commuter_ids.add(person.id)
            if i % 500_000 == 0:
                logger.info(f"Assigned {i} of {len(world.people)} commuters...")
        logger.info(f"Commuters assigned")
        for city in world.cities:
            if city.external or not city.stations:
                continue
            else:
                internal = len(city.commuter_ids)
                external = len(
                    list(
                        chain.from_iterable(
                            station.commuter_ids for station in city.stations
                        )
                    )
                )
                logger.info(
                    f"City {city.name} has {internal} people commuting internally"
                    f" and {external} people commuting externally."
                )

    def create_transport_units_at_stations_and_cities(
        self, world, people_per_city_transport=50, people_per_inter_city_transport=50
    ):
        logger.info(f"Creating transport units for the population")
        world.city_transports = CityTransports([])
        world.inter_city_transports = InterCityTransports([])
        for city in world.cities:
            if city.has_stations:
                n_commute_internal = len(city.commuter_ids)
                number_city_transports = int(
                    np.ceil(n_commute_internal / people_per_city_transport)
                )
                for _ in range(number_city_transports):
                    city_transport = CityTransport()
                    city.city_transports.append(city_transport)
                    world.city_transports.add(city_transport)
                for station in city.stations:
                    number_inter_city_transports = int(
                        np.ceil(
                            len(station.commuter_ids) / people_per_inter_city_transport
                        )
                    )
                    for _ in range(number_inter_city_transports):
                        inter_city_transport = InterCityTransport()
                        station.inter_city_transports.append(inter_city_transport)
                        world.inter_city_transports.add(inter_city_transport)
        logger.info(f"Cities' transport initialised")

    def get_commute_subgroup(self, person):
        work_city = person.work_city
        if work_city is None or not person.mode_of_transport.is_public:
            return
        subgroup = work_city.get_commute_subgroup(person)
        person.subgroups.commute = subgroup
        return subgroup
