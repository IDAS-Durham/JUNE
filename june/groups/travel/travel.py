# Standard library imports
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
from typing import List, Optional, Set, TYPE_CHECKING
import random

# Third-party imports
import numpy as np
import pandas as pd
import yaml

# JUNE imports
from june.paths import configs_path, data_path
from june.demography.person import Person
from june.geography import Cities, Stations
# Remove world import to break circular dependency
# from june.world import World 
from june.groups import Subgroup
from .mode_of_transport import ModeOfTransport, ModeOfTransportGenerator
from .transport import CityTransports, InterCityTransports
from .aircraft import Aircraft, Aircrafts
from .foreign_destination import TravelPurpose, RiskLevel, ForeignDestinationRegistry

# Use TYPE_CHECKING for World import to avoid circular dependency
if TYPE_CHECKING:
    from june.world import World

# Constants
logger = logging.getLogger("travel")
default_cities_filename = data_path / "input/geography/cities_per_super_area_ew.csv"
default_city_stations_config_filename = configs_path / "defaults/travel/city_stations.yaml"
default_commute_config_filename = configs_path / "defaults/groups/travel/commute.yaml"
default_international_config_filename = configs_path / "defaults/groups/travel/international.yaml"


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

        import pandas as pd

        # Load city-super area mappings
        city_super_areas = pd.read_csv(self.city_super_areas_filename)

        # Summary
        print("\n===== City to Super Area Mapping Summary =====")
        print(f"Total Cities: {city_super_areas['city'].nunique()}")
        print(f"Total Super Areas: {city_super_areas['super_area'].nunique()}")
        print("\nSample of Cities and Their Super Areas:")
        print(city_super_areas.head(10))

    def initialise_commute(
        self, world: "World", maximum_number_commuters_per_city_station: int = 200000
    ) -> None:
        """Initialize commuting patterns"""
        logger.info("Initialising commute...")
        try:
            # Generate cities
            self._generate_cities(
                world=world, city_super_areas_filename=self.city_super_areas_filename
            )
            
            # If cities couldn't be generated, skip the rest of commute initialization
            if not hasattr(world, 'cities') or not world.cities:
                logger.warning("No cities found. Skipping commute initialization.")
                return
                
            # Assign transportation modes to people
            self._assign_mode_of_transport_to_people(world=world)
            
            # Get city commuters
            commuters_dict = self._get_city_commuters(
                world=world, city_stations_filename=self.city_stations_filename
            )
            
            # Skip if no commuters found
            if not commuters_dict or all(len(v['internal']) + len(v['external']) == 0 for v in commuters_dict.values()):
                logger.warning("No commuters found. Skipping station creation.")
                return
                
            # Create stations
            self._create_stations(
                world=world,
                commuters_dict=commuters_dict,
                maximum_number_commuters_per_city_station=maximum_number_commuters_per_city_station,
                city_stations_filename=self.city_stations_filename,
            )
            
            # Skip if no stations created
            if not hasattr(world, 'stations') or not world.stations:
                logger.warning("No stations created. Skipping commuter distribution and transport creation.")
                return
                
            # Distribute commuters to stations
            self._distribute_commuters_to_stations(
                world=world, commuters_dict=commuters_dict
            )
            
            # Create transport in cities
            self._create_transports_in_cities(world)
            
            logger.info("Commute initialization completed successfully.")
        except Exception as e:
            logger.error(f"Error initialising commute: {e}")
            logger.warning("Continuing without commuting functionality.")
            # Ensure world.stations exists to prevent later crashes
            if not hasattr(world, 'stations'):
                world.stations = []

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

        # Collect data for visualization
        city_data = []
        
        for city in world.cities:
            city_data.append({
                "City Name": city.name,
                "Coordinates": city.coordinates,
                "Assigned Super Areas": ", ".join(city.super_areas),
                "Primary Super Area": city.super_area.name if city.super_area else "None"
            })
        
        # Convert collected data to a DataFrame for visualization
        df_cities = pd.DataFrame(city_data)
        print("\n===== Summary of Generated Cities =====")
        print(df_cities)

        city_names = [city.name for city in world.cities]
        if len(city_names) > 0:
            logger.info(
                f"This world has {len(city_names)} cities, with names\n" f"{city_names}"
            )
        else:
            logger.info("This world has no important cities in it")

    def _assign_mode_of_transport_to_people(self, world: "World"):
        """
        Assigns a mode of transport (public or not) to the world's population.
        """
        logger.info("Determining people mode of transport")
        mode_of_transport_generator = ModeOfTransportGenerator.from_file()

        # Collect data for visualization
        transport_data = []

        for i, area in enumerate(world.areas):
            if i % 4000 == 0:
                logger.info(
                    f"Mode of transport allocated in {i} of {len(world.areas)} areas."
                )
            mode_of_transport_generator_area = (
                mode_of_transport_generator.regional_gen_from_area(area.name)
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
                # Collect data for each person
                transport_data.append({
                    "Person ID": person.id,
                    "Area": area.name,
                    "Age": person.age,
                    "Mode of Transport": person.mode_of_transport.description,
                    "Is Public": person.mode_of_transport.is_public
                })

        # Convert collected data to DataFrame for visualization
        df_transport = pd.DataFrame(transport_data).sample(10)  # Display a random sample of 10 people
        print("\n===== Sample of People with Assigned Mode of Transport =====")
        print(df_transport)
        logger.info("Mode of transport determined for everyone.")

    def _get_city_commuters(self, world: "World", city_stations_filename: str):
        """
        Gets internal and external commuters per city, providing both summary counts and a sample of commuters' details.
        Handles cases where cities, stations or transport modes may be missing.
        """
        try:
            # Safely load cities with stations config
            try:
                with open(city_stations_filename) as f:
                    cities_with_stations = yaml.load(f, Loader=yaml.FullLoader)["number_of_inter_city_stations"]
            except (FileNotFoundError, KeyError) as e:
                logger.warning(f"Error loading city stations file: {e}")
                logger.warning("Continuing with empty cities with stations list.")
                cities_with_stations = {}

            commuter_data = {}
            commuter_samples = []  # List to store commuter samples for visualization

            # Initialize commuter data structure for each city with stations
            if hasattr(world, 'cities') and world.cities:
                for city in world.cities:
                    if city.name in cities_with_stations:
                        commuter_data[city.name] = {"internal": [], "external": []}
            else:
                logger.warning("No cities found in world. Skipping commuter assignment.")
                return {}

            # Skip processing if no cities have stations
            if not commuter_data:
                logger.warning("No cities with stations found. Skipping commuter assignment.")
                return {}

            logger.info("Assigning commuters to stations...")

            # Process each person for commuter assignment and collect sample data
            people_count = len(world.people.people) if hasattr(world.people, 'people') else 0
            
            for i, person in enumerate(world.people or []):
                try:
                    # Check if person has required attributes
                    if not hasattr(person, 'mode_of_transport') or not person.mode_of_transport:
                        continue
                        
                    if person.mode_of_transport.is_public:
                        commute_type = None
                        
                        # Check if work_city exists and is in cities_with_stations
                        if (hasattr(person, 'work_city') and person.work_city and 
                            person.work_city.name in cities_with_stations):
                            
                            # Check if home_city exists
                            if hasattr(person, 'home_city') and person.home_city:
                                if person.home_city == person.work_city:
                                    commute_type = "internal"
                                    commuter_data[person.work_city.name]["internal"].append(person.id)
                                else:
                                    commute_type = "external"
                                    commuter_data[person.work_city.name]["external"].append(person.id)

                        # Collect sample data for each commuter
                        if commute_type:
                            commuter_samples.append({
                                "Person ID": person.id,
                                "Home City": person.home_city.name if hasattr(person, 'home_city') and person.home_city else "Unknown",
                                "Work City": person.work_city.name if hasattr(person, 'work_city') and person.work_city else "Unknown",
                                "Mode of Transport": person.mode_of_transport.description,
                                "Commuter Type": commute_type
                            })
                except AttributeError as e:
                    logger.debug(f"Skipping person {getattr(person, 'id', 'unknown')}: {e}")
                    continue

                if i % 500_000 == 0 and i > 0:
                    logger.info(f"Assigned {i} of {people_count} potential commuters...")

            logger.info("Commuters assigned")

            # Prepare summary of commuters by city
            commuter_summary = [
                {
                    "City": city,
                    "Internal Commuters": len(data["internal"]),
                    "External Commuters": len(data["external"]),
                    "Total Commuters": len(data["internal"]) + len(data["external"])
                }
                for city, data in commuter_data.items()
                if len(data["internal"]) + len(data["external"]) > 0
            ]
            
            # Display summaries and samples
            if commuter_summary:
                df_commuter_summary = pd.DataFrame(commuter_summary)
                print("\n===== Summary of Commuters by City =====")
                print(df_commuter_summary)
            else:
                print("\n===== No commuters found =====")

            if commuter_samples:
                # Sample up to 10 commuters, but don't fail if fewer are available
                sample_size = min(10, len(commuter_samples))
                if sample_size > 0:
                    df_commuter_samples = pd.DataFrame(commuter_samples).sample(n=sample_size)
                    print("\n===== Sample of Commuters with Transport Mode and Commuter Type =====")
                    print(df_commuter_samples)

            return commuter_data
            
        except Exception as e:
            logger.error(f"Error getting city commuters: {e}")
            return {}  # Return empty dict to allow continuation

    def _create_stations(
    self,
    world: "World",
    city_stations_filename: str,
    commuters_dict: dict,
    maximum_number_commuters_per_city_station: int,
):
        """
        Generates cities, super stations, and stations on the given world.
        Handles cases where cities or super areas might be missing.
        """
        try:
            # Safely load inter-city stations configuration
            try:
                with open(city_stations_filename) as f:
                    inter_city_stations_per_city = yaml.load(f, Loader=yaml.FullLoader)["number_of_inter_city_stations"]
            except (FileNotFoundError, KeyError) as e:
                logger.warning(f"Error loading inter-city stations file: {e}")
                logger.warning("Continuing with empty inter-city stations list.")
                inter_city_stations_per_city = {}

            logger.info("Creating stations...")
            world.stations = Stations([])  # Initialize world stations collection even if empty

            station_data = []  # List to collect sample data for visualization
            
            # Check if cities and super areas are available
            if not hasattr(world, 'cities') or not world.cities:
                logger.warning("No cities found in world. Skipping station creation.")
                return
                
            if not hasattr(world, 'super_areas') or not world.super_areas:
                logger.warning("No super areas found in world. Skipping station creation.")
                return

            # Skip if no cities have stations defined
            has_stations = False
            for city in world.cities:
                if city.name in inter_city_stations_per_city:
                    has_stations = True
                    break
                    
            if not has_stations:
                logger.warning("No cities with stations defined. Skipping station creation.")
                return
                
            # Process each city that has stations defined
            for city in world.cities:
                if city.name not in inter_city_stations_per_city:
                    continue

                try:
                    # Setup inter-city stations
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

                    # Calculate the number of city stations based on internal commuters
                    # Default to 0 if city not in commuters_dict or no internal commuters
                    n_internal_commuters = 0
                    if city.name in commuters_dict and "internal" in commuters_dict[city.name]:
                        n_internal_commuters = len(commuters_dict[city.name]["internal"])
                        
                    n_city_stations = int(
                        np.ceil(n_internal_commuters / maximum_number_commuters_per_city_station)
                    ) if n_internal_commuters > 0 else 0
                    
                    # Create city stations if needed
                    if n_city_stations > 0:
                        city.city_stations = Stations.from_city_center(
                            city=city,
                            super_areas=world.super_areas,
                            number_of_stations=n_city_stations,
                            type="city_station",
                            distance_to_city_center=5,
                        )
                        city.city_stations._construct_ball_tree()
                        world.stations += city.city_stations
                    else:
                        # Ensure city_stations exists but is empty
                        city.city_stations = Stations([])

                    logger.info(
                        f"City {city.name} has {n_city_stations} city "
                        f"and {n_inter_city_stations} inter-city stations."
                    )

                    # Collect data for visualization
                    station_data.append({
                        "City": city.name,
                        "Number of City Stations": n_city_stations,
                        "Number of Inter-City Stations": n_inter_city_stations,
                        "Total Internal Commuters": n_internal_commuters
                    })
                except Exception as e:
                    logger.warning(f"Error creating stations for city {city.name}: {e}")
                    # Ensure city has empty station collections to prevent crashes
                    city.inter_city_stations = Stations([])
                    city.city_stations = Stations([])
                    continue

            # If no stations were created, return early
            if not world.stations or len(world.stations) == 0:
                logger.warning("No stations created. Skipping station to super area mapping.")
                return

            # Assign closest inter-city stations to each super area
            try:
                for super_area in world.super_areas:
                    # Initialize the dictionary if it doesn't exist
                    if not hasattr(super_area, 'closest_inter_city_station_for_city'):
                        super_area.closest_inter_city_station_for_city = {}
                        
                    for city in world.cities:
                        # Check if city has stations before trying to get closest station
                        if hasattr(city, 'inter_city_stations') and city.inter_city_stations:
                            try:
                                super_area.closest_inter_city_station_for_city[
                                    city.name
                                ] = city.get_closest_inter_city_station(super_area.coordinates)
                            except Exception as e:
                                logger.debug(f"Could not assign closest station from {city.name} to {super_area.name}: {e}")
            except Exception as e:
                logger.warning(f"Error assigning closest stations to super areas: {e}")

            # Visualize the station data summary if stations were created
            if station_data:
                df_station_summary = pd.DataFrame(station_data)
                print("\n===== Summary of Stations Created by City =====")
                print(df_station_summary)
            else:
                print("\n===== No Stations Created =====")
                
        except Exception as e:
            logger.error(f"Error creating stations: {e}")
            # Ensure world.stations exists even if creation fails
            world.stations = Stations([])

    def _distribute_commuters_to_stations(self, world: "World", commuters_dict: dict):
        """
        Distributes commuters to their respective stations in the world.
        Handles cases where components may be missing.
        """
        try:
            # Skip if no cities or no commuters
            if not hasattr(world, 'cities') or not world.cities:
                logger.warning("No cities found. Skipping commuter distribution.")
                return
                
            if not commuters_dict:
                logger.warning("No commuters found. Skipping commuter distribution.")
                return
                
            commuter_data = []  # Collect data for visualization

            for city_name, commuters in commuters_dict.items():
                try:
                    # Get city by name, skip if not found
                    city = None
                    try:
                        city = world.cities.get_by_name(city_name)
                    except (AttributeError, KeyError) as e:
                        logger.warning(f"City {city_name} not found: {e}")
                        continue
                        
                    if not city:
                        continue
                    
                    # Assign internal commuters to the city if there are any
                    if "internal" in commuters and commuters["internal"]:
                        city.internal_commuter_ids = set(commuters["internal"])
                        
                        # Log internal commuters with station information (up to 5)
                        sample_ids = list(city.internal_commuter_ids)[:min(5, len(city.internal_commuter_ids))]
                        for commuter_id in sample_ids:
                            try:
                                commuter = world.people.get_from_id(commuter_id)
                                commuter_data.append({
                                    "Person ID": commuter_id,
                                    "Home City": commuter.home_city.name if hasattr(commuter, 'home_city') and commuter.home_city else "Unknown",
                                    "Work City": commuter.work_city.name if hasattr(commuter, 'work_city') and commuter.work_city else "Unknown",
                                    "Mode of Transport": commuter.mode_of_transport.description if hasattr(commuter, 'mode_of_transport') else "Unknown",
                                    "Commuter Type": "internal",
                                    "Assigned Station": "City Station"  # Internal commuters use city stations
                                })
                            except Exception as e:
                                logger.debug(f"Error processing internal commuter {commuter_id}: {e}")
                                continue

                    # Assign external commuters to respective inter-city stations if there are any
                    if "external" in commuters and commuters["external"]:
                        for external_commuter_id in commuters["external"]:
                            try:
                                external_commuter = world.people.get_from_id(external_commuter_id)
                                
                                # Skip if commuter doesn't have required attributes
                                if not (hasattr(external_commuter, 'work_city') and 
                                        external_commuter.work_city and 
                                        hasattr(external_commuter, 'super_area') and 
                                        external_commuter.super_area):
                                    continue
                                    
                                work_city = external_commuter.work_city.name
                                
                                # Skip if super_area doesn't have the required dictionary
                                if (not hasattr(external_commuter.super_area, 'closest_inter_city_station_for_city') or
                                    work_city not in external_commuter.super_area.closest_inter_city_station_for_city):
                                    continue
                                    
                                station = external_commuter.super_area.closest_inter_city_station_for_city[work_city]
                                
                                # Skip if station is None or doesn't have commuter_ids attribute
                                if not station or not hasattr(station, 'commuter_ids'):
                                    continue
                                    
                                station.commuter_ids.add(external_commuter_id)
                                
                                # Log external commuter data
                                commuter_data.append({
                                    "Person ID": external_commuter_id,
                                    "Home City": external_commuter.home_city.name if hasattr(external_commuter, 'home_city') and external_commuter.home_city else "Unknown",
                                    "Work City": work_city,
                                    "Mode of Transport": external_commuter.mode_of_transport.description if hasattr(external_commuter, 'mode_of_transport') else "Unknown",
                                    "Commuter Type": "external",
                                    "Assigned Station": station.id if hasattr(station, 'id') else "Unknown"
                                })
                            except Exception as e:
                                logger.debug(f"Error processing external commuter {external_commuter_id}: {e}")
                                continue
                except Exception as e:
                    logger.warning(f"Error distributing commuters for city {city_name}: {e}")
                    continue

            # Display commuter data if available
            if commuter_data:
                # Convert collected commuter data to a DataFrame for better readability
                df_commuter_data = pd.DataFrame(commuter_data)
                print("\n===== Sample of Commuters with Transport Mode, Commuter Type, and Assigned Station =====")
                print(df_commuter_data.head(min(10, len(commuter_data))))  # Display a sample of the data
            else:
                print("\n===== No commuters were distributed to stations =====")
                
        except Exception as e:
            logger.error(f"Error distributing commuters to stations: {e}")
            # Continue even if distribution fails

    def _create_transports_in_cities(
    self, world, seats_per_city_transport=50, seats_per_inter_city_transport=50
    ):
        """
        Creates city transports and inter city transports in CityStations and
        InterCityStations respectively. Handles cases where components may be missing.
        """
        try:
            logger.info("Creating transport units for the population")
            
            # Skip if no cities
            if not hasattr(world, 'cities') or not world.cities:
                logger.warning("No cities found. Skipping transport creation.")
                return
                
            # Initialize transport collections if they don't exist
            if not hasattr(world, "city_transports"):
                world.city_transports = CityTransports([])
            if not hasattr(world, "inter_city_transports"):
                world.inter_city_transports = InterCityTransports([])

            transport_data = []  # Collect data for visualization
            
            # Process each city
            for city in world.cities:
                try:
                    # Skip cities without stations
                    if not hasattr(city, 'has_stations') or not city.has_stations:
                        continue
                        
                    # Get seats per passenger from config, default to 1 if not found
                    seats_per_passenger = 1
                    if hasattr(self, 'commute_config') and self.commute_config and "seats_per_passenger" in self.commute_config:
                        seats_per_passenger = self.commute_config["seats_per_passenger"].get(city.name, 1)
                    
                    # Create city transports if city has city stations and internal commuters
                    if hasattr(city, 'city_stations') and city.city_stations and hasattr(city, 'internal_commuter_ids'):
                        try:
                            n_commute_internal = len(city.internal_commuter_ids)
                            if n_commute_internal > 0 and len(city.city_stations) > 0:
                                number_city_transports = int(
                                    np.ceil((seats_per_passenger * n_commute_internal / seats_per_city_transport))
                                )
                                logger.info(f"City {city.name} has {number_city_transports} city train carriages.")
                                
                                # Assign city transports
                                n_city_stations = len(city.city_stations)
                                transports_per_station = int(np.ceil(number_city_transports / n_city_stations))
                                for station in city.city_stations:
                                    try:
                                        # Initialize city_transports if it doesn't exist
                                        if not hasattr(station, 'city_transports'):
                                            station.city_transports = []
                                            
                                        for _ in range(transports_per_station):
                                            city_transport = world.city_transports.venue_class(station=station)
                                            station.city_transports.append(city_transport)
                                            world.city_transports.add(city_transport)
                                            transport_data.append({
                                                "Assigned Transport ID": city_transport.id,
                                                "Station": station.id,
                                                "City": city.name,
                                                "Transport Type": "City"
                                            })
                                            number_city_transports -= 1
                                            if number_city_transports <= 0:
                                                break
                                    except Exception as e:
                                        logger.debug(f"Error creating city transport for station {getattr(station, 'id', 'unknown')} in {city.name}: {e}")
                                        continue
                        except Exception as e:
                            logger.warning(f"Error creating city transports for {city.name}: {e}")
                    
                    # Create inter-city transports if city has inter-city stations
                    if hasattr(city, 'inter_city_stations') and city.inter_city_stations:
                        try:
                            number_inter_city_transports_total = 0
                            for station in city.inter_city_stations:
                                try:
                                    # Skip stations without commuter IDs or with empty commuter IDs
                                    if not hasattr(station, 'commuter_ids') or len(station.commuter_ids) == 0:
                                        continue
                                        
                                    # Initialize inter_city_transports if it doesn't exist
                                    if not hasattr(station, 'inter_city_transports'):
                                        station.inter_city_transports = []
                                    
                                    number_inter_city_transports = int(
                                        np.ceil(
                                            (seats_per_passenger * len(station.commuter_ids) / seats_per_inter_city_transport)
                                        )
                                    )
                                    number_inter_city_transports_total += number_inter_city_transports
                                    
                                    for _ in range(number_inter_city_transports):
                                        inter_city_transport = world.inter_city_transports.venue_class(station=station)
                                        station.inter_city_transports.append(inter_city_transport)
                                        world.inter_city_transports.add(inter_city_transport)
                                        transport_data.append({
                                            "Assigned Transport ID": inter_city_transport.id,
                                            "Station": station.id,
                                            "City": city.name,
                                            "Transport Type": "Inter-city"
                                        })
                                except Exception as e:
                                    logger.debug(f"Error creating inter-city transport for station {getattr(station, 'id', 'unknown')} in {city.name}: {e}")
                                    continue
                                        
                            logger.info(f"City {city.name} has {number_inter_city_transports_total} inter-city train carriages.")
                        except Exception as e:
                            logger.warning(f"Error creating inter-city transports for {city.name}: {e}")
                except Exception as e:
                    logger.warning(f"Error processing city {city.name}: {e}")
                    continue

            # Display transport data if available
            if transport_data:
                # Convert collected transport data to a DataFrame for better readability
                df_transport_data = pd.DataFrame(transport_data)
                sample_size = min(10, len(transport_data))
                print("\n===== Summary of Created Transport Units by City and Station =====")
                print(df_transport_data.sample(sample_size))  # Display a sample of the data
            else:
                print("\n===== No Transport Units Created =====")

            logger.info("Cities' transport initialized")
        except Exception as e:
            logger.error(f"Error creating transports in cities: {e}")
            # Continue even if transport creation fails


@dataclass
class TravelItinerary:
    """Tracks a person's international travel journey"""
    person_id: int
    destination: str
    purpose: TravelPurpose
    departure_date: datetime
    return_date: datetime
    companions: Set[int]

    @property
    def duration_days(self) -> int:
        """Calculate duration in days"""
        return (self.return_date - self.departure_date).days


class InternationalTravel:
    """Handles international travel activities"""
    
    def __init__(self, international_config_filename=default_international_config_filename):
        self.active_travelers = {}  # person_id -> (return_date, original_subgroups)
        self.travel_groups = {}     # group_id -> set of person_ids traveling together
        self._next_group_id = 0

        with open(international_config_filename) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        self.destination_registry = ForeignDestinationRegistry()

    def get_international_subgroup(self, person: Person) -> Optional[Subgroup]:
        """
        Check if person should be traveling internationally and return appropriate subgroup
        """
        if person.id in self.active_travelers:
            return self.get_travel_subgroup(person)
        return None
        
    def get_travel_subgroup(self, world: "World", person: "Person") -> Optional[Subgroup]:
        """Get appropriate airport/aircraft subgroup for traveling person"""
        if person.id not in self.active_travelers:
            return None
            
        # Find nearest departure airport
        departure_airport = world.airports.get_closest_airport(person.area.coordinates)
        
        # Get available aircraft at airport
        aircraft = departure_airport.get_available_aircraft()
        
        if aircraft and not aircraft.is_full:
            # Get the travel group this person belongs to
            group_id = None
            for gid, members in self.travel_groups.items():
                if person.id in members:
                    group_id = gid
                    break

            subgroup = aircraft.get_subgroup(person)
            
            # Apply infection risk correlation for travel groups
            if group_id is not None:
                correlation_factor = self._get_group_correlation_factor(group_id)
                subgroup.infection_correlation = correlation_factor
                
            return subgroup
        
        return None

    def _get_group_correlation_factor(self, group_id: int) -> float:
        """
        Get infection correlation factor based on group type
        """
        # Count number of infected people in the group
        n_infected = 0
        n_total = 0
        
        for person_id in self.travel_groups[group_id]:
            person = Person.find_by_id(person_id)
            if person:
                n_total += 1
                if person.infected:
                    n_infected += 1

        # If no one is infected, return 1.0 (normal risk)
        if n_infected == 0:
            return 1.0

        # Get correlation factors from config
        correlation_factors = self.config["infection_correlation"]
        
        # Determine if this is a family or friend group based on residence
        first_person = Person.find_by_id(next(iter(self.travel_groups[group_id])))
        if not first_person:
            return 1.0
            
        sample_residence = first_person.residence.group if first_person.residence else None
        is_family_group = all(
            Person.find_by_id(pid).residence.group == sample_residence
            for pid in self.travel_groups[group_id]
            if Person.find_by_id(pid)
        )

        # Apply increasing correlation based on number of infected
        base_factor = correlation_factors["family"] if is_family_group else correlation_factors["friends"]
        infection_ratio = n_infected / n_total
        
        # Exponential increase in risk as more group members are infected
        return base_factor * (1 + infection_ratio)

    def select_travelers(self, world: "World", date: datetime) -> List[Person]:
        """
        Select individuals for international travel based on various factors.
        
        Parameters
        ----------
        world : World
            The world containing people and regions
        date : datetime
            Current simulation date
            
        Returns
        -------
        List[Person]
            List of selected travelers
        """
        # Get config parameters
        base_prob = self.config["selection"]["base_daily_probability"]
        age_multipliers = self.config["selection"]["age_multipliers"]
        weekend_multiplier = self.config["selection"]["weekend_multiplier"]
        monthly_multipliers = self.config["selection"]["monthly_multipliers"]
        
        # Time-based modifiers
        is_weekend = date.weekday() >= 5
        time_multiplier = weekend_multiplier if is_weekend else 1.0
        season_multiplier = monthly_multipliers[str(date.month)]
        
        selected_travelers = []
        
        # Consider each person for travel
        for person in world.people:
            # Skip if person can't travel
            if (person.id in self.active_travelers or  # Already traveling
                person.age < 18 or  # Too young
                person.infected or  # Infected
                person.medical_facility or  # In hospital
                person.busy):  # Busy with other activity
                continue
                
            # Get age-based multiplier
            age_mult = 1.0
            for age_range, multiplier in age_multipliers.items():
                min_age, max_age = map(int, age_range.split("-"))
                if min_age <= person.age <= max_age:
                    age_mult = multiplier
                    break

            # Final probability calculation
            travel_prob = (base_prob * 
                         age_mult * 
                         time_multiplier * 
                         season_multiplier)
            
            # Randomly select based on probability
            if random.random() < travel_prob:
                selected_travelers.append(person)
                
        # Log selection summary
        n_selected = len(selected_travelers)
        logger.info(f"\n=== Travel Selection Summary for {date} ===")
        logger.info(f"Base probability: {base_prob:.4f}")
        logger.info(f"Weekend multiplier applied: {is_weekend}")
        logger.info(f"Monthly multiplier for {date.month}: {monthly_multipliers[str(date.month)]}")
        logger.info(f"Selected {n_selected} travelers from {len(world.people)} eligible people")
        
        return selected_travelers

    def schedule_trip(self, person: "Person", world: "World", date: datetime) -> Optional[TravelItinerary]:
        """
        Schedule a complete international trip including purpose, duration, 
        companions and destination.
        
        Parameters
        ----------
        person : Person
            Person initiating travel
        world : World
            The world containing people and regions
        date : datetime
            Current simulation date
            
        Returns
        -------
        Optional[TravelItinerary]
            Complete travel itinerary if successfully scheduled, None otherwise
        """
        try:
            # Determine travel purpose based on person demographics
            purpose = self._determine_travel_purpose(person)
            
            # Get trip duration based on purpose
            duration = self._get_duration_for_purpose(purpose)
            return_date = date + timedelta(days=duration)

            # Select destination and get its risk profile
            destination_name = self._select_destination(purpose)
            destination = self.destination_registry.get_destination(destination_name)
            
            if not destination:
                raise ValueError(f"Could not find destination: {destination_name}")
            
            # Calculate infection risk for stay duration
            risk = destination.calculate_infection_risk(
                duration_days=duration,
                travel_purpose=purpose
            )
            
            # Get travel companions based on purpose
            companions = self._get_travel_companions(person, purpose)
            
            # Create travel itinerary
            itinerary = TravelItinerary(
                person_id=person.id,
                destination=destination_name,
                purpose=purpose,
                departure_date=date,
                return_date=return_date,
                companions=companions
            )
            
            # Store travelers and override their activities
            self._process_travelers(itinerary, world)

            logger.info(f"\n=== New Trip Scheduled ===")
            logger.info(f"Primary Traveler: {person.id}")
            logger.info(f"Destination: {destination_name} (Risk Level: {destination.risk_level.name})")
            logger.info(f"Purpose: {purpose.name}")
            logger.info(f"Duration: {duration} days")
            logger.info(f"Infection Risk: {risk:.2%}")
            logger.info(f"Companions: {len(companions)} people")
            
            return itinerary
            
        except Exception as e:
            logger.error(f"Error scheduling trip for person {person.id}: {e}")
            return None

    def _determine_travel_purpose(self, person: Person) -> TravelPurpose:
        """Determine if trip is business or leisure based on demographics"""
        base_business_prob = 0.7 if 25 <= person.age <= 65 else 0.2
        
        # Adjust for time of year (more leisure in summer)
        month = person.world.timer.date.month
        if 6 <= month <= 8:  # Summer months
            base_business_prob *= 0.7  # Reduce business probability
            
        return (TravelPurpose.BUSINESS 
                if random.random() < base_business_prob 
                else TravelPurpose.LEISURE)

    def _get_duration_for_purpose(self, purpose: TravelPurpose) -> int:
        """
        Get trip duration based on travel purpose.
        
        Parameters
        ----------
        purpose : TravelPurpose
            Purpose of travel (business or leisure)
        
        Returns
        -------
        int:
            Number of days for the trip
        """
        if purpose == TravelPurpose.BUSINESS:
            # Business: 2-7 days, weighted toward shorter durations
            possible_days = range(2, 8)  # 2-7 days inclusive
            # Exponentially decreasing weights favoring shorter trips
            weights = [np.exp(-0.5 * (day - 2)) for day in possible_days]
            # Normalize weights
            weights = np.array(weights) / sum(weights)
            
            duration = np.random.choice(possible_days, p=weights)
            
        else:  # LEISURE
            # Leisure: 3-14 days, weighted toward middle range (7-10 days)
            possible_days = range(3, 15)  # 3-14 days inclusive
            
            # Create bell-shaped weights centered around 8.5 days
            weights = [
                np.exp(-0.3 * ((day - 8.5) ** 2)) 
                for day in possible_days
            ]
            # Normalize weights
            weights = np.array(weights) / sum(weights)
            
            duration = np.random.choice(possible_days, p=weights)
        
        return duration

    def _select_destination(self, purpose: TravelPurpose) -> str:
        """Select destination country based on travel purpose"""
        # Get all destinations filtered by purpose-appropriate risk level
        if purpose == TravelPurpose.BUSINESS:
            # Business travelers prefer lower risk destinations
            destinations = self.destination_registry.get_destinations_by_risk(RiskLevel.LOW)
            # Add some medium risk if not enough options
            if len(destinations) < 3:
                destinations.extend(
                    self.destination_registry.get_destinations_by_risk(RiskLevel.MEDIUM)
                )
        else:  # LEISURE
            # Leisure travelers accept medium risk
            destinations = self.destination_registry.get_destinations_by_risk(RiskLevel.MEDIUM)
            destinations.extend(
                self.destination_registry.get_destinations_by_risk(RiskLevel.LOW)
            )
            
        if not destinations:
            raise ValueError("No suitable destinations found")
            
        # Calculate weights based on risk levels
        weights = []
        for dest in destinations:
            # Base weight inversely proportional to risk
            weight = 1.0 / dest.risk_multiplier
            
            # Adjust weight based on purpose
            if purpose == TravelPurpose.BUSINESS:
                weight *= 1.5 if dest.risk_level == RiskLevel.LOW else 1.0
            else:
                weight *= 1.2 if dest.risk_level == RiskLevel.MEDIUM else 1.0
            
            weights.append(weight)
            
        # Normalize weights
        total = sum(weights)
        weights = [w/total for w in weights]
        
        # Random weighted selection
        chosen = random.choices(destinations, weights=weights, k=1)[0]
        return chosen.name

    def _get_travel_companions(self, person: Person, purpose: TravelPurpose) -> Set[int]:
        """Get travel companions based on purpose and household"""
        companions = set()
        
        # Solo travel more likely for business
        if purpose == TravelPurpose.BUSINESS:
            return companions
            
        # For leisure, check household members
        if (hasattr(person, "residence") and 
            person.residence and 
            hasattr(person.residence.group, "residents")):
            
            # Get probabilities from config
            household_prob = self.config.get("household_travel_probability", 0.8)
            
            if random.random() < household_prob:
                # Add eligible household members
                for member in person.residence.group.residents:
                    if (member.id != person.id and
                        member.id not in self.active_travelers and
                        not member.infected and
                        not member.medical_facility and
                        (member.age < 18 or random.random() < 0.8)):
                        companions.add(member.id)
                        
        return companions

    def _process_travelers(self, itinerary: "TravelItinerary", world: "World"):
        """Process all travelers in itinerary and override their activities"""
        all_travelers = {itinerary.person_id} | itinerary.companions
        destination = self.destination_registry.get_destination(itinerary.destination)
        
        for person_id in all_travelers:
            traveler = world.people.get_from_id(person_id)
            if traveler:
                # Start travel tracking
                traveler.start_travel(destination, itinerary.departure_date)
                
                # Set activity overrides
                traveler.set_activity_override(
                    "residence", 
                    itinerary.return_date,
                    None  # Will be assigned by airport/aircraft
                )
                traveler.set_activity_override(
                    "primary_activity",
                    itinerary.return_date, 
                    None
                )
                
                # Store in active travelers
                self.active_travelers[person_id] = (
                    itinerary.return_date,
                    {
                        "residence": traveler.residence,
                        "primary_activity": traveler.primary_activity
                    }
                )

        # Register as travel group if multiple travelers
        if len(all_travelers) > 1:
            self.travel_groups[self._next_group_id] = all_travelers
            self._next_group_id += 1

    def process_returns(self, world: "World", date: datetime):
        """Process returning travelers and restore their activities"""
        returned_travelers = []
        
        for person_id, (return_date, _) in self.active_travelers.items():
            if date >= return_date:
                # Clear activity overrides
                person = world.people.get_from_id(person_id)
                if person:
                    person.clear_activity_override("residence")
                    person.clear_activity_override("primary_activity")
                returned_travelers.append(person_id)

        # Remove processed travelers
        for person_id in returned_travelers:
            self.active_travelers.pop(person_id)
            
            # Remove from travel groups if present
            for group_id, members in list(self.travel_groups.items()):
                if person_id in members:
                    members.remove(person_id)
                    if not members:  # If group is empty
                        del self.travel_groups[group_id]
                    break
