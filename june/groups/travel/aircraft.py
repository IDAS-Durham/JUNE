from enum import IntEnum
from typing import List, Optional, Set
import random
import numpy as np
import yaml

from june.groups import Group, Subgroup, Supergroup
from june.groups.group.interactive import InteractiveGroup
from june.demography.person import Person
from june.paths import configs_path

class Aircraft(Group):
    """Aircraft represents a plane used for international travel"""
    
    #class SubgroupType(IntEnum):
    #    passengers = 0  # Single subgroup since aircraft is treated as confined space
    
    def __init__(
        self, 
        airport=None, 
        flight_duration: float = 3.0,
    ):
        super().__init__()
        self.airport = airport
        self.flight_duration = flight_duration
        self._config = self._load_config()
        
        # Initialize aircraft layout
        self.num_seats = self._config["num_rows"] * self._config["num_seats_per_row"]
        self.capacity = self.num_seats
        
        # Create single passengers subgroup
        self.subgroups = [Subgroup(self, self.SubgroupType.passengers)]
        
        # Track occupancy
        self._occupied_seats = 0

    def _load_config(self):
        """Load aircraft parameters from config"""
        config_path = configs_path / "defaults/groups/travel/aircrafts.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    @property
    def is_full(self) -> bool:
        """Check if aircraft is at capacity"""
        return self._occupied_seats >= self.capacity

    def add(self, person: Person, activity: str = "international_travel", subgroup_type=None) -> bool:
        """Add passenger to aircraft"""
        if self.is_full:
            return False
            
        # Add to single passengers subgroup
        super().add(person, activity=activity, subgroup_type=self.SubgroupType.passengers)
        self._occupied_seats += 1
        return True

    def remove(self, person: Person) -> None:
        """Remove passenger from aircraft"""
        super().remove_person(person)
        self._occupied_seats -= 1

    def get_interactive_group(self, people_from_abroad=None) -> InteractiveGroup:
        """Create interactive group using InteractiveAircraft"""
        return InteractiveAircraft(self, people_from_abroad=people_from_abroad)


class InteractiveAircraft(InteractiveGroup):
    def __init__(self, group: "Aircraft", people_from_abroad=None):
        super().__init__(group=group, people_from_abroad=people_from_abroad)
        self.characteristic_time = group.flight_duration

    def get_processed_contact_matrix(self, contact_matrix):
        """
        Process contact matrix based on current aircraft state.
        Calculates n_infected/n_total ratio.
        """
        ret = np.zeros((1, 1))
        
        # Count total and infected passengers
        total_passengers = len(self.group.subgroups[0].people)
        infected_passengers = sum(1 for p in self.group.subgroups[0].people if p.infected)
        
        # Calculate infection ratio
        if total_passengers > 0:
            infection_ratio = infected_passengers / total_passengers
        else:
            infection_ratio = 0
            
        # Apply base rate scaled by infection ratio
        base_rate = contact_matrix[0][0]
        ret[0, 0] = base_rate * infection_ratio
        
        # Additional duration effect for long flights
        if self.group.flight_duration > 8:
            # Increase risk by up to 50% for flights over 8 hours
            long_flight_factor = 1.0 + min(0.5, (self.group.flight_duration - 8)/8)
            ret *= long_flight_factor
            
        return ret


class Aircrafts(Supergroup):
    """Collection of aircraft"""
    venue_class = Aircraft

    def __init__(self, aircrafts: List[Aircraft]):
        super().__init__(members=aircrafts)

    @classmethod
    def for_airport(cls, airport, n_aircrafts: int = 10) -> "Aircrafts":
        """Create aircraft collection for a specific airport"""
        aircrafts = []
        for _ in range(n_aircrafts):
            aircraft = Aircraft(airport=airport)
            aircrafts.append(aircraft)
        return cls(aircrafts)

    @classmethod
    def from_airports(cls, airports) -> "Aircrafts":
        """Create aircraft fleet for multiple airports"""
        all_aircrafts = []
        for airport in airports:
            # Scale number of aircraft based on daily passenger capacity
            n_aircrafts = max(1, int(airport.capacity / 200))
            airport_aircrafts = cls.for_airport(airport, n_aircrafts)
            all_aircrafts.extend(airport_aircrafts.members)
            
        return cls(all_aircrafts)

    def get_available_aircraft(self, airport) -> Optional[Aircraft]:
        """Get an available aircraft at the given airport"""
        available = [
            aircraft for aircraft in self.members 
            if aircraft.airport == airport and not aircraft.is_full
        ]
        return random.choice(available) if available else None
