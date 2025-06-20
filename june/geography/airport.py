import yaml
import logging
from enum import IntEnum
from typing import List, Optional
import numpy as np
import pandas as pd
import random

from june.paths import configs_path, data_path
from june.demography.person import Person
from june.geography import Geography, Areas, Area, SuperArea
from june.groups import Group, Supergroup
from june.groups.group.interactive import InteractiveGroup

default_airports_filename = data_path / "input/geography/uk_airports.csv"
default_config_filename = configs_path / "defaults/geography/airports.yaml"

logger = logging.getLogger("airports")

class Airport(Group):
    """An airport represents an international travel hub"""
    
    # class SubgroupType(IntEnum):
    #     travelers = 0  # Only one subgroup type

    def __init__(
        self,
        area: Area = None,
        coordinates: tuple = None,
        super_area: SuperArea = None,
        name: str = None,
        capacity: int = 1000,
        max_concurrent_occupancy: Optional[int] = None,
    ):
        # Initialize base group first
        super().__init__()
        
        # Initialize empty airports list for area if needed
        if area is not None and not hasattr(area, 'airports'):
            area.airports = []
            
        # Set instance attributes directly
        self._area = area
        self._super_area = super_area
        self._coordinates = coordinates
        self._name = name
        self._capacity = capacity
        self._max_concurrent_occupancy = max_concurrent_occupancy or int(capacity * 0.1)
        self._config = self.from_config()  # Load config at initialization

    # Add property getters and setters
    @property
    def area(self):
        return self._area
    
    @area.setter
    def area(self, value):
        self._area = value

    @property
    def super_area(self):
        return self._super_area
    
    @super_area.setter
    def super_area(self, value):
        self._super_area = value

    @property
    def coordinates(self):
        return self._coordinates
    
    @coordinates.setter
    def coordinates(self, value):
        self._coordinates = value

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value

    @property
    def capacity(self):
        return self._capacity
    
    @capacity.setter
    def capacity(self, value):
        self._capacity = value

    @property
    def max_concurrent_occupancy(self):
        return self._max_concurrent_occupancy
    
    @max_concurrent_occupancy.setter
    def max_concurrent_occupancy(self, value):
        self._max_concurrent_occupancy = value

    @property
    def config(self):
        return self._config

    @classmethod 
    def from_config(cls, config_filename=default_config_filename):
        """Initialize airport parameters from config"""
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return config

    @property
    def crowding_factor(self) -> float:
        """Calculate infection risk multiplier based on current occupancy"""
        current_occupancy = self.size  # Current number of travelers
        occupancy_ratio = current_occupancy / self.max_concurrent_occupancy
        
        # Base multiplier from config
        base_weight = self.config["area_weights"]["airport"]
        
        # Exponential crowding effect when occupancy > 50% capacity
        if occupancy_ratio > 0.5:
            crowding_multiplier = np.exp(occupancy_ratio - 0.5)
        else:
            crowding_multiplier = 1.0
            
        return base_weight * crowding_multiplier

    def add(self, person: Person, activity: str = "international_travel", 
            travel_class: str = "economy", subgroup_type=None):
        """
        Add person to travelers subgroup with class-specific processing time

        Parameters
        ----------
        person : Person
            The person to add
        activity : str
            The activity type (default: international_travel)  
        travel_class : str
            The travel class (economy/business/first) affecting processing time
        subgroup_type : SubgroupType, optional
            The subgroup type to add to
        """
        if not self.is_full:
            # Get processing time for travel class
            processing_time = self.config["processing_times"].get(travel_class, 3.0)
            
            # Scale contact rate by processing time
            time_factor = processing_time / 24.0  # Convert to fraction of day
            
            # Store processing time with person for this visit
            if not hasattr(person, 'airport_processing_time'):
                setattr(person, 'airport_processing_time', {})
            person.airport_processing_time[self.id] = time_factor
            
            # Add to subgroup
            super().add(person, activity=activity, 
                       subgroup_type=self.SubgroupType.travelers)
            return True
        return False

    @property 
    def is_full(self):
        """Check if airport is at max concurrent occupancy"""
        return self.size >= self.max_concurrent_occupancy

    def get_interactive_group(self, people_from_abroad=None):
        """
        Create interactive group with infection model:
        P_transmission = β_airport * t_overlap * c_interaction
        P_airport_infection = 1 - ∏(1 - P_transmission,i)
        """
        interactive_group = InteractiveGroup(self, people_from_abroad=people_from_abroad)
        
        # Get β_airport from config
        beta_airport = self.config["contact_matrices"]["travelers"]["travelers"]
        
        # Initialize dictionary for susceptible exposures
        susceptible_exposure = {}  # {susceptible_id: [(inf_id, trans_prob), ...]}

        # Calculate individual transmission probabilities
        for subgroup in self.subgroups:
            # Get infected and susceptible people
            infected = [p for p in subgroup.people if p.infected]
            susceptible = [p for p in subgroup.people if not p.infected]

            # For each infected-susceptible pair
            for inf in infected:
                # Get infected person's time overlap
                inf_time = (
                    inf.airport_processing_time.get(self.id, 0.125) 
                    if hasattr(inf, 'airport_processing_time') 
                    else 0.125
                )
                
                for sus in susceptible:
                    # Get susceptible person's time overlap
                    sus_time = (
                        sus.airport_processing_time.get(self.id, 0.125)
                        if hasattr(sus, 'airport_processing_time')
                        else 0.125
                    )
                    
                    # Calculate effective time overlap
                    t_overlap = min(inf_time, sus_time)
                    
                    # Get contact intensity from crowding
                    c_interaction = self.crowding_factor
                    
                    # Calculate transmission probability
                    p_transmission = (
                        beta_airport * 
                        t_overlap * 
                        c_interaction
                    )

                    # Store probability for this pair
                    if sus.id not in susceptible_exposure:
                        susceptible_exposure[sus.id] = []
                    susceptible_exposure[sus.id].append((inf.id, p_transmission))

        # Convert individual probabilities to cumulative risk
        final_transmission_probs = {}
        for sus_id, exposures in susceptible_exposure.items():
            # Calculate cumulative probability using 1 - ∏(1 - p_i)
            cumulative_prob = 1 - np.prod([
                (1 - p) for _, p in exposures
            ])
            final_transmission_probs[sus_id] = cumulative_prob

        # Set interaction parameters for JUNE framework
        beta = -np.log(1 - np.mean(list(final_transmission_probs.values())))
        interactive_group.contact_factor = beta
        interactive_group.area_factor = self.crowding_factor
        interactive_group.physical_contact_ratio = self.config["physical_contact_ratio"]
        
        return interactive_group

    @property
    def region(self):
        return self.super_area.region

class Airports(Supergroup):
    """Collection of airports"""
    venue_class = Airport
    
    def __init__(self, airports: List[Airport]):
        super().__init__(members=airports)
        self._ball_tree = None

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        data_file: str = default_airports_filename,
        config_file: str = default_config_filename,
    ) -> "Airports":
        """Create airports for the given geography"""
        return cls.for_areas(geography.areas, data_file, config_file)

    @classmethod
    def for_areas(
        cls,
        areas: Areas,
        data_file: str = default_airports_filename,
        config_file: str = default_config_filename,
     ) -> "Airports":
        """Creates Airports for specified areas"""
        return cls.from_file(areas, data_file, config_file)

    @classmethod
    def from_file(
        cls,
        areas: Areas,
        data_file: str = default_airports_filename,
        config_file: str = default_config_filename,
    ) -> "Airports":
        """
        Initialize Airports from data and config files.

        Parameters
        ----------
        areas: Areas
            Areas object to assign airports to
        data_file: str
            Path to CSV with airport data (name, coordinates, capacity)
        config_file: str
            Path to YAML with airport configuration parameters

        Returns
        -------
        Airports
            Collection of airport objects
        """
        try:
            # First initialize empty airports list for all areas
            for area in areas:
                if not hasattr(area, 'airports'):
                    area.airports = []

            # Validate config file
            with open(config_file) as f:
                config = yaml.safe_load(f)
                required_config = ["capacity_scaling", "area_weights", "contact_matrices"]
                if not all(key in config for key in required_config):
                    raise ValueError(f"Airport config must contain: {required_config}")
            
            # Read and validate airport data
            airports_df = pd.read_csv(data_file)
            required_cols = ["name", "latitude", "longitude", "passengers_per_year"]
            if not all(col in airports_df.columns for col in required_cols):
                raise ValueError(f"Airport data must contain columns: {required_cols}")
            
            # Filter to airports within area bounds
            area_bounds = areas.get_bounds()  # Get geographical bounds of areas
            airports_df = airports_df[
                (airports_df.latitude >= area_bounds["min_lat"]) &
                (airports_df.latitude <= area_bounds["max_lat"]) &
                (airports_df.longitude >= area_bounds["min_lon"]) &
                (airports_df.longitude <= area_bounds["max_lon"])
            ]
        
            if airports_df.empty:
                logger.warning("No airports found within geography bounds")
                return cls([])
            
            logger.info(f"Found {len(airports_df)} airports within geography bounds")
            
            # Build airports
            return cls.build_airports_for_areas(
                areas=areas,
                airports_df=airports_df,
                config=config
            )
        
        except Exception as e:
            logger.error(f"Error initializing airports: {e}")
            raise

    @classmethod
    def _log_sample_airports(cls, areas: Areas):
        """
        Log a sample of airports for visualization purposes.
        
        Parameters
        ----------
        areas: Areas
            Areas containing airports to sample from
        """
        sampled_airports = []
        for area in areas:
            if hasattr(area, 'airports') and area.airports:
                sample = random.sample(area.airports, min(5, len(area.airports)))
                for airport in sample:
                    sampled_airports.append({
                        "| Airport ID": airport.id,
                        "| Name": airport.name,
                        "| Area": area.name,
                        "| Region": airport.region.name if airport.region else "Unknown",
                        "| Coordinates": airport.coordinates,
                        "| Daily Capacity": airport.capacity
                    })

        if sampled_airports:
            df_sample = pd.DataFrame(sampled_airports)
            logger.info("\n===== Sample of Created Airports =====")
            logger.info("\n" + df_sample.to_string())
        else:
            logger.warning("No airports found in any areas")
        
    @classmethod
    def build_airports_for_areas(
        cls,
        areas: Areas,
        airports_df: pd.DataFrame,
        config: dict = None,
    ) -> "Airports":
        """Build airports for specified areas using data and config"""
        config = config or {}
        airports = []

        # Get parameters from config
        max_concurrent_ratio = config.get("capacity_scaling", {}).get("max_concurrent_occupancy", 0.1)
        
        for _, row in airports_df.iterrows():
            coordinates = (row.latitude, row.longitude)
            area = areas.get_closest_area(coordinates)
            
            daily_capacity = int(row.passengers_per_year / 365)
            airport = cls.venue_class(
                area=area,
                coordinates=coordinates, 
                super_area=area.super_area,
                name=row.name,
                capacity=daily_capacity,  # Daily capacity
                max_concurrent_occupancy=int(daily_capacity * max_concurrent_ratio)
            )

            # Add airport to lists
            airports.append(airport)
            if not hasattr(area, 'airports'):
                area.airports = []
            area.airports.append(airport)

        cls._log_sample_airports(areas)

        return cls(airports)
