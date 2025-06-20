from enum import IntEnum
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import yaml

from june.paths import configs_path

class TravelPurpose(IntEnum):
    BUSINESS = 1
    LEISURE = 2

class RiskLevel(IntEnum):
    LOW = 1
    MEDIUM = 2 
    HIGH = 3

@dataclass
class ForeignDestination:
    """
    Represents an international travel destination with associated infection risk.
    Uses model: P = 1 - exp(-β_base * R_country * D_stay)
    """
    name: str
    risk_level: RiskLevel
    risk_multiplier: float
    region: Optional[str] = None
    _config: dict = None  # Cache config

    def __post_init__(self):
        """Load config after initialization"""
        config_path = configs_path / "defaults/geography/foreign_destinations.yaml"
        with open(config_path) as f:
            self._config = yaml.safe_load(f)
    
    def calculate_infection_risk(
        self, 
        duration_days: int,
        travel_purpose: TravelPurpose = TravelPurpose.BUSINESS,
    ) -> float:
        """
        Calculate infection risk based on destination risk and travel purpose.
        P = 1 - exp(-β_base * R_country * D_stay)
        
        Parameters
        ----------
        duration_days: int
            Length of stay in days (D_stay)
        travel_purpose: TravelPurpose 
            Purpose of travel affecting base transmission rate
            
        Returns
        -------
        float:
            Infection probability (0-1)
        """
        # Get base transmission rate and adjust by travel purpose
        beta_base = self._config["base_parameters"]["contact_rate"]
        duration_scaling = self._config["base_parameters"]["duration_scaling"]
        activity_multiplier = self._config["activity_intensities"][travel_purpose.name]
        beta_adjusted = beta_base * activity_multiplier
        
        # Calculate cumulative risk using the exponential model
        # P = 1 - exp(-β_base * R_country * D_stay)
        cumulative_risk = 1 - np.exp(
            -beta_adjusted * 
            self.risk_multiplier * 
            duration_days / duration_scaling  # Scale factor to keep probabilities reasonable
        )
        
        return cumulative_risk

class ForeignDestinationRegistry:
    """Registry of foreign destinations and their risk levels"""
    
    def __init__(self):
        self.destinations: Dict[str, ForeignDestination] = {}
        self._load_destinations()
        
    def _load_destinations(self):
        """Load destination data from config"""
        config_path = configs_path / "defaults/geography/foreign_destinations.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Get base risk multipliers for each level
        risk_multipliers = config["risk_multipliers"]
        
        # Create destinations from config
        for dest_name, dest_data in config["destinations"].items():
            # Get risk level and use corresponding multiplier
            risk_level = RiskLevel[dest_data["risk_level"]]
            
            # Use configured risk multiplier or base level multiplier
            risk_multiplier = dest_data.get(
                "risk_multiplier", 
                risk_multipliers[risk_level.name]
            )
            
            self.destinations[dest_name] = ForeignDestination(
                name=dest_name,
                risk_level=risk_level,
                risk_multiplier=risk_multiplier,
                region=dest_data.get("region")
            )

    def get_destination(self, name: str) -> Optional[ForeignDestination]:
        """Get destination by name"""
        return self.destinations.get(name)

    def get_destinations_by_risk(self, risk_level: RiskLevel) -> List[ForeignDestination]:
        """Get all destinations with specified risk level"""
        return [
            dest for dest in self.destinations.values() 
            if dest.risk_level == risk_level
        ]

    def get_destinations_by_region(self, region: str) -> List[ForeignDestination]:
        """Get all destinations in specified region"""
        return [
            dest for dest in self.destinations.values() 
            if dest.region == region
        ]