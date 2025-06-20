"""
Infection Seeding Configuration Loader

This module loads YAML configuration files and converts them into the DataFrame
structures required by the June epidemiology simulation infection seeds.

All clustered/exact seeds must use the msoa_specific_cases format.
"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
import logging

from june.epidemiology.infection_seed.infection_seed import InfectionSeed, InfectionSeeds
from june.epidemiology.infection_seed.exact_num_infection_seed import (
    ExactNumInfectionSeed,
    ExactNumClusteredInfectionSeed
)
from june import paths

logger = logging.getLogger(__name__)

# ============================================================================
# DEFAULT CONFIGURATION LOCATION
# ============================================================================
DEFAULT_SEEDING_CONFIG_PATH = paths.configs_path / "defaults/epidemiology/infection_seeds/infection_seeds_timeline.yaml"


class SeedingConfigLoader:
    """Loads and processes infection seeding configuration from YAML files."""
    
    def __init__(self, config_path: Union[str, Path]):
        """
        Initialise the configuration loader.
        
        Parameters
        ----------
        config_path : str or Path
            Path to the YAML configuration file.
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.global_params = self.config.get('global_parameters', {})
    
    @classmethod
    def from_file(cls, config_path: Optional[Union[str, Path]] = None) -> 'SeedingConfigLoader':
        """
        Create a SeedingConfigLoader from a configuration file.
        
        Parameters
        ----------
        config_path : str, Path, or None
            Path to the YAML configuration file. If None, uses the default location.
            
        Returns
        -------
        SeedingConfigLoader
            Configured loader instance
        """
        if config_path is None:
            config_path = DEFAULT_SEEDING_CONFIG_PATH
            logger.info(f"Using default seeding configuration: {config_path}")
        else:
            config_path = Path(config_path)
            
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        return cls(config_path)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the YAML configuration file."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"Successfully loaded seeding configuration from {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_path}: {e}")
            raise
    
    def create_infection_seeds(self, world, infection_selector) -> InfectionSeeds:
        """
        Create InfectionSeeds object from the configuration.
        
        Parameters
        ----------
        world : World
            The simulation world object
        infection_selector : InfectionSelector
            The infection selector to use for seeding
            
        Returns
        -------
        InfectionSeeds
            Collection of all configured infection seeds
        """
        seeds = []
        
        for seed_config in self.config.get('infection_seeds', []):
            try:
                seed = self._create_single_seed(seed_config, world, infection_selector)
                if seed:
                    seeds.append(seed)
                    logger.info(f"Created seed: {seed_config.get('name', 'unnamed')}")
            except Exception as e:
                logger.error(f"Failed to create seed {seed_config.get('name', 'unnamed')}: {e}")
                # Don't raise here - log the error but continue with other seeds
                continue
        
        if not seeds:
            raise ValueError("No valid infection seeds could be created from configuration")
        
        logger.info(f"Successfully created {len(seeds)} infection seeds")
        return InfectionSeeds(seeds)
    
    def _create_single_seed(self, seed_config: Dict[str, Any], world, infection_selector):
        """Create a single infection seed from configuration."""
        seed_type = seed_config.get('type', '').lower()
        
        if seed_type == 'uniform':
            return self._create_uniform_seed(seed_config, world, infection_selector)
        elif seed_type in ['clustered', 'exact']:
            return self._create_structured_seed(seed_config, world, infection_selector, seed_type)
        else:
            raise ValueError(f"Unknown seed type: {seed_type}")
    
    def _create_uniform_seed(self, seed_config: Dict[str, Any], world, infection_selector):
        """Create a uniform infection seed."""
        # Get parameters with fallbacks to global defaults
        params = seed_config.get('parameters', {})
        base_cpc = self.global_params.get('base_cases_per_capita', 0.000002)
        
        # Calculate cases per capita
        if 'cases_per_capita' in params:
            cases_per_capita = params['cases_per_capita']
        elif 'cases_per_capita_multiplier' in params:
            cases_per_capita = base_cpc * params['cases_per_capita_multiplier']
        else:
            cases_per_capita = base_cpc
        
        return InfectionSeed.from_uniform_cases(
            world=world,
            infection_selector=infection_selector,
            cases_per_capita=cases_per_capita,
            date=seed_config['date'],
            seed_past_infections=params.get(
                'seed_past_infections', 
                self.global_params.get('default_seed_past_infections', True)
            ),
            seed_strength=params.get(
                'seed_strength',
                self.global_params.get('default_seed_strength', 1.0)
            )
        )
    
    def _create_structured_seed(self, seed_config: Dict[str, Any], world, infection_selector, seed_type: str):
        """Create a structured (exact/clustered) infection seed."""
        # All structured seeds must use msoa_specific_cases format
        if 'msoa_specific_cases' not in seed_config:
            raise ValueError(f"Seed '{seed_config.get('name', 'unnamed')}' of type '{seed_type}' must use 'msoa_specific_cases' format")
        
        # Create DataFrame from msoa_specific_cases
        df = self._create_dataframe_from_msoa_specific_cases(seed_config)
        
        # Get parameters
        params = seed_config.get('parameters', {})
        seed_past_infections = params.get(
            'seed_past_infections',
            self.global_params.get('default_seed_past_infections', True)
        )
        seed_strength = params.get(
            'seed_strength',
            self.global_params.get('default_seed_strength', 1.0)
        )
        
        # Choose appropriate seed class
        if seed_type == 'clustered':
            return ExactNumClusteredInfectionSeed(
                world=world,
                infection_selector=infection_selector,
                daily_cases_per_capita_per_age_per_region=df,
                seed_past_infections=seed_past_infections,
                seed_strength=seed_strength
            )
        else:  # exact
            return ExactNumInfectionSeed(
                world=world,
                infection_selector=infection_selector,
                daily_cases_per_capita_per_age_per_region=df,
                seed_past_infections=seed_past_infections,
                seed_strength=seed_strength
            )
    
    def _create_dataframe_from_msoa_specific_cases(self, seed_config: Dict[str, Any]) -> pd.DataFrame:
        """
        Create DataFrame from msoa_specific_cases configuration.
        
        Expected format:
        msoa_specific_cases:
          age_groups: ["20-75"]
          msoas_and_cases:
            "E02001368": [6]
            "E02000560": [4]
            "E02000293": [4]
            "E02000578": [4]
        """
        # Parse date
        date = pd.to_datetime(seed_config['date'])
        
        # Get msoa-specific data
        msoa_data = seed_config['msoa_specific_cases']
        age_bins = msoa_data['age_groups']
        msoas_and_cases = msoa_data['msoas_and_cases']
        
        # Validate that we have the required fields
        if not age_bins:
            raise ValueError(f"Seed '{seed_config.get('name', 'unnamed')}': age_groups cannot be empty")
        if not msoas_and_cases:
            raise ValueError(f"Seed '{seed_config.get('name', 'unnamed')}': msoas_and_cases cannot be empty")
        
        # Create MultiIndex
        multi_index = pd.MultiIndex.from_product(
            [[date], age_bins], 
            names=["date", "age"]
        )
        
        # Get all msoas and their case values
        msoas = list(msoas_and_cases.keys())
        
        # Build data array: rows = age groups, columns = msoas
        data = []
        for age_idx, age_bin in enumerate(age_bins):
            row = []
            for msoa in msoas:
                cases_for_msoa = msoas_and_cases[msoa]
                if isinstance(cases_for_msoa, list):
                    # Use the appropriate index for this age group
                    if age_idx < len(cases_for_msoa):
                        row.append(cases_for_msoa[age_idx])
                    else:
                        raise ValueError(
                            f"Seed '{seed_config.get('name', 'unnamed')}': "
                            f"MSOA '{msoa}' has {len(cases_for_msoa)} values but "
                            f"there are {len(age_bins)} age groups. Values must match age groups."
                        )
                else:
                    # Single value applies to all age groups
                    row.append(cases_for_msoa)
            data.append(row)
        
        df = pd.DataFrame(
            data=data,
            index=multi_index,
            columns=msoas
        )
        
        logger.debug(f"Created DataFrame with shape {df.shape} for seed '{seed_config.get('name', 'unnamed')}' on {date}")
        return df
    
    def validate_config(self) -> List[str]:
        """
        Validate the configuration and return any errors found.
        
        Returns
        -------
        List[str]
            List of validation error messages. Empty if no errors.
        """
        errors = []
        
        # Check required top-level keys
        if 'infection_seeds' not in self.config:
            errors.append("Missing 'infection_seeds' section in configuration")
            return errors
        
        # Validate each seed
        for i, seed_config in enumerate(self.config['infection_seeds']):
            seed_errors = self._validate_single_seed(seed_config, i)
            errors.extend(seed_errors)
        
        return errors
    
    def _validate_single_seed(self, seed_config: Dict[str, Any], index: int) -> List[str]:
        """Validate a single seed configuration."""
        errors = []
        prefix = f"Seed {index + 1} ({seed_config.get('name', 'unnamed')})"
        
        # Required fields
        required_fields = ['type', 'date', 'name']
        for field in required_fields:
            if field not in seed_config:
                errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate type
        valid_types = ['uniform', 'clustered', 'exact']
        seed_type = seed_config.get('type', '').lower()
        if seed_type not in valid_types:
            errors.append(f"{prefix}: Invalid type '{seed_type}'. Must be one of {valid_types}")
        
        # Validate date format
        try:
            pd.to_datetime(seed_config.get('date', ''))
        except Exception:
            errors.append(f"{prefix}: Invalid date format '{seed_config.get('date', '')}'")
        
        # Type-specific validation
        if seed_type in ['clustered', 'exact']:
            # Must use msoa_specific_cases format
            if 'msoa_specific_cases' not in seed_config:
                errors.append(f"{prefix}: {seed_type} seeds must use 'msoa_specific_cases' format")
            else:
                msoa_data = seed_config['msoa_specific_cases']
                
                # Validate required fields in msoa_specific_cases
                if 'age_groups' not in msoa_data:
                    errors.append(f"{prefix}: Missing 'age_groups' in msoa_specific_cases")
                elif not isinstance(msoa_data['age_groups'], list) or not msoa_data['age_groups']:
                    errors.append(f"{prefix}: 'age_groups' must be a non-empty list")
                
                if 'msoas_and_cases' not in msoa_data:
                    errors.append(f"{prefix}: Missing 'msoas_and_cases' in msoa_specific_cases")
                elif not isinstance(msoa_data['msoas_and_cases'], dict) or not msoa_data['msoas_and_cases']:
                    errors.append(f"{prefix}: 'msoas_and_cases' must be a non-empty dictionary")
                else:
                    # Validate each msoa's case values
                    age_groups = msoa_data.get('age_groups', [])
                    for msoa, cases in msoa_data['msoas_and_cases'].items():
                        if isinstance(cases, list):
                            if len(cases) != len(age_groups):
                                errors.append(
                                    f"{prefix}: MSOA '{msoa}' has {len(cases)} values but "
                                    f"there are {len(age_groups)} age groups. Must match."
                                )
                            for case_val in cases:
                                if not isinstance(case_val, (int, float)) or case_val < 0:
                                    errors.append(f"{prefix}: Invalid case value for MSOA '{msoa}': {case_val}")
                        elif not isinstance(cases, (int, float)) or cases < 0:
                            errors.append(f"{prefix}: Invalid case value for MSOA '{msoa}': {cases}")
        
        elif seed_type == 'uniform':
            params = seed_config.get('parameters', {})
            if 'cases_per_capita' not in params and 'cases_per_capita_multiplier' not in params:
                # Check if global base is defined
                if 'base_cases_per_capita' not in self.global_params:
                    errors.append(f"{prefix}: Uniform seed requires either 'cases_per_capita', 'cases_per_capita_multiplier', or global 'base_cases_per_capita'")
        
        return errors
    
    def print_summary(self):
        """Print a summary of the loaded configuration."""
        print(f"\n=== Seeding Configuration Summary ===")
        print(f"Configuration file: {self.config_path}")
        
        seeds = self.config.get('infection_seeds', [])
        print(f"Total seeds configured: {len(seeds)}")
        
        # Group by type
        type_counts = {}
        date_range = []
        
        for seed in seeds:
            seed_type = seed.get('type', 'unknown')
            type_counts[seed_type] = type_counts.get(seed_type, 0) + 1
            
            try:
                date_range.append(pd.to_datetime(seed['date']))
            except:
                pass
        
        print("\nSeed types:")
        for seed_type, count in type_counts.items():
            print(f"  {seed_type}: {count}")
        
        # Show date range
        if date_range:
            print(f"\nSeeding date range:")
            print(f"  First: {min(date_range).strftime('%Y-%m-%d %H:%M')}")
            print(f"  Last: {max(date_range).strftime('%Y-%m-%d %H:%M')}")
        
        # Show global parameters
        if self.global_params:
            print(f"\nGlobal parameters:")
            for key, value in self.global_params.items():
                print(f"  {key}: {value}")
        
        # Show msoa-specific seeds details
        clustered_seeds = [s for s in seeds if s.get('type', '').lower() in ['clustered', 'exact']]
        if clustered_seeds:
            print(f"\nMSOA-specific seeds: {len(clustered_seeds)}")
            for seed in clustered_seeds:
                msoa_data = seed.get('msoa_specific_cases', {})
                msoas = list(msoa_data.get('msoas_and_cases', {}).keys())
                age_groups = msoa_data.get('age_groups', [])
                print(f"  {seed.get('name', 'unnamed')}: {len(msoas)} msoas, {len(age_groups)} age groups")
        
        print("=" * 40)
