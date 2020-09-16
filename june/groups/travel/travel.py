import logging
import yaml
from random import randint
from typing import List
from enum import IntEnum
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

from june.paths import configs_path, data_path
from june.geography import Cities, Stations, SuperStations, Station
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

default_commute_config_filenmame = configs_path / "defaults/groups/travel/commute.yaml"
default_super_stations_filename = (
    data_path / "input/geography/stations_per_super_area_ew.csv"
)
default_cities_filename = data_path / "input/geography/cities_per_super_area_ew.csv"


def generate_commuting_network(
    world,
    commute_config_filename=default_commute_config_filenmame,
    city_super_areas_filename=default_cities_filename,
    super_stations_filename=default_super_stations_filename,
):
    """
    Generates cities, super stations, and stations on the given world.
    """
    with open(commute_config_filename) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    # initialise cities
    logger.info("Creating cities...")
    world.cities = Cities.for_super_areas(
        world.super_areas, city_super_areas_filename=city_super_areas_filename
    )
    world.stations = Stations([])
    for city in world.cities:
        city.stations = Stations([])
        city.super_stations = SuperStations.for_city(city, super_stations_filename)
        # by default, 4 stations per super station, unless specified in the config file
        if city.name in config["cities"]:
            n_stations_per_super_station = config["cities"][
                "n_stations_per_super_station"
            ]
        else:
            n_stations_per_super_station = 4
        for super_station in city.super_stations:
            super_station.stations = Stations.for_super_station(
                super_station=super_station,
                super_areas=world.super_areas,
                number_of_stations=n_stations_per_super_station,
                distance_to_super_station=50,
            )
            city.stations += super_station.stations
            world.stations += super_station.stations
        if city.stations.members:
            city.stations._construct_ball_tree()
    if not world.stations.members:
        logger.warning("No stations in this world, travel won't work")
        return
    for super_area in world.super_areas:
        super_area.closest_commuting_city = world.cities.get_closest_commuting_city(super_area.coordinates)
        super_area.closest_station = super_area.closest_commuting_city.stations.get_closest_station(
            super_area.coordinates
        )


class Travel:
    """
    This class handles all functionality related to travel, from local commute,
    to inter-city and inter-regional travel.
    """

    def __init__(self):
        pass

    def assign_mode_of_transport_to_people(self, world):
        """
        Assigns a mode of transport (public or not) to the world's population
        """
        mode_of_transport_generator = ModeOfTransportGenerator.from_file()
        for area in world.areas:
            mode_of_transport_generator_area = mode_of_transport_generator.regional_gen_from_msoarea(
                area.name
            )
            for person in area.people:
                person.mode_of_transport = (
                    mode_of_transport_generator_area.weighted_random_choice()
                )

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
        if world.cities is None or len(world.cities) == 0:
            logger.warning(f"No cities initialised in this world, no one will commute.")
            return

        logger.info(f"Assigning commuters to stations...")
        commuters_per_city = defaultdict(int)
        for i, person in enumerate(world.people):
            if person.mode_of_transport.is_public:
                if person.work_city is not None:
                    if person.home_city == person.work_city:
                        # this person commutes internally
                        person.work_city.commuters.append(person)
                    else:
                        # commutes away to an external station
                        person.area.super_area.closest_station.commuters.append(person)
            if i % 500_000 == 0:
                logger.info(f"Assigned {i} of {len(world.people)} commuters...")
        logger.info(f"Commuters assigned")

    def create_transport_units_at_stations_and_cities(
        self, world, people_per_city_transport=50, people_per_inter_city_transport=50
    ):
        logger.info(f"Creating transport units for the population")
        world.city_transports = CityTransports([])
        world.inter_city_transports = InterCityTransports([])
        for city in world.cities:
            n_commute_internal = len(city.commuters)
            number_city_transports = int(
                np.ceil(n_commute_internal / people_per_city_transport)
            )
            for _ in range(number_city_transports):
                city.city_transports.append(CityTransport())
            world.city_transports.members += city.city_transports
            for station in city.stations:
                number_inter_city_transports = int(
                    np.ceil(len(station.commuters) / people_per_inter_city_transport)
                )
                for _ in range(number_inter_city_transports):
                    station.inter_city_transports.append(InterCityTransport())
                world.inter_city_transports.members += station.inter_city_transports
        logger.info(f"Cities' transport initialised")

    def get_commute_subgroup(self, person):
        work_city = person.work_city
        if work_city is None or not person.mode_of_transport.is_public:
            return
        return work_city.get_commute_subgroup(person)
        # if work_city.external:

        # closest_super_station = person.super_area.closest_super_station
        # if person in work_city.commute_internal:
        #    idx = randint(len(work_city))
        #    return person.work_super_area.closest_city_transports[idx]
        # else:
        #    idx = randint(len(person.work_super_area.closest_inter_city_transports))
        #    return person.work_super_area.closest_inter_city_transports[idx]
