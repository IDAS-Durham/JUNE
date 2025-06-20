import os
import tables
import pandas as pd
import yaml
import numpy as np
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict
import logging
import time

# MPI imports from wrapper
from june.mpi_wrapper import mpi_comm, mpi_size, mpi_available

# June imports
import june
from june.records.event_records_writer import (
    InfectionRecord,
    HospitalAdmissionsRecord,
    ICUAdmissionsRecord,
    DischargesRecord,
    DeathsRecord,
    RecoveriesRecord,
    SymptomsRecord,
    VaccinesRecord,
)
from june.records.static_records_writer import (
    PeopleRecord,
    LocationRecord,
    AreaRecord,
    SuperAreaRecord,
    RegionRecord,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from june.world import World
    from june.interaction.interaction import Interaction
    from june.epidemiology.infection_seed.infection_seed import InfectionSeeds
    from june.epidemiology.infection import InfectionSelectors
    from june.epidemiology.epidemiology import Epidemiology
    from june.activity.activity_manager import ActivityManager

# Set up logging
logger = logging.getLogger("records_writer")
mpi_logger = logging.getLogger("mpi_records")

class Record:
    """
    Handles the recording of simulation events and results.
    Enhanced with improved MPI support for distributed simulations.
    Works in both MPI and non-MPI modes.
    """
    
    def __init__(
        self, record_path: str, record_static_data=False, mpi_rank: Optional[int] = None
    ):
        """
        Initialize the Record class with MPI awareness.
        
        Parameters
        ----------
        record_path : str
            Path to save record files
        record_static_data : bool, optional
            Whether to record static data
        mpi_rank : int, optional
            MPI rank of the current process, if not provided, uses global mpi_rank
        """
        start_time = time.time()
        self.record_path = Path(record_path)
        self.record_path.mkdir(parents=True, exist_ok=True)
        
        # Use global mpi_rank if not specified
        self.mpi_rank = mpi_rank if mpi_rank is not None else globals().get('mpi_rank', 0)
        
        # Set up filenames based on MPI rank and availability
        if mpi_available and mpi_size > 1 and self.mpi_rank is not None:
            self.filename = f"june_record.{self.mpi_rank}.h5"
            self.summary_filename = f"summary.{self.mpi_rank}.csv"
            self.demographic_filename = f"detailed_demographic_summary.{self.mpi_rank}.csv"
            self.current_status_filename = f"current_status_by_msoa.{self.mpi_rank}.csv"
        else:
            # In non-MPI mode or single process, use simple filenames
            self.filename = "june_record.h5"
            self.summary_filename = "summary.csv"
            self.demographic_filename = "detailed_demographic_summary.csv"
            self.current_status_filename = "current_status_by_msoa.csv"
            
        self.configs_filename = "config.yaml"
        self.record_static_data = record_static_data
        
        # Clean up any existing files
        try:
            os.remove(self.record_path / self.filename)
        except OSError:
            pass
            
        # Initialize record files
        filename = self.record_path / self.filename
        self._initialize_events(filename)
        
        if self.record_static_data:
            self._initialize_statics()
            
        self._create_summary_file()
        self._create_config_file()
        
        # Log initialization time
        end_time = time.time()
        if mpi_available and self.mpi_rank is not None:
            logger.info(f"Rank {self.mpi_rank}: Record initialization took {end_time - start_time:.2f} seconds")
        else:
            logger.info(f"Record initialization took {end_time - start_time:.2f} seconds")
        
    def _initialize_events(self, filename):
        """
        Initialize event record structures.
        
        Parameters
        ----------
        filename : Path
            Path to the HDF5 file
        """
        self.events = {
            "infections": InfectionRecord(hdf5_filename=filename),
            "hospital_admissions": HospitalAdmissionsRecord(hdf5_filename=filename),
            "icu_admissions": ICUAdmissionsRecord(hdf5_filename=filename),
            "discharges": DischargesRecord(hdf5_filename=filename),
            "deaths": DeathsRecord(hdf5_filename=filename),
            "recoveries": RecoveriesRecord(hdf5_filename=filename),
            "symptoms": SymptomsRecord(hdf5_filename=filename),
            "vaccines": VaccinesRecord(hdf5_filename=filename),
        }
    
    def _initialize_statics(self):
        """Initialize static record structures."""
        self.statics = {
            "people": PeopleRecord(),
            "locations": LocationRecord(),
            "areas": AreaRecord(),
            "super_areas": SuperAreaRecord(),
            "regions": RegionRecord(),
        }
    
    def _create_summary_file(self):
        """Create and initialize the summary CSV file."""
        with open(
            self.record_path / self.summary_filename, "w", newline=""
        ) as summary_file:
            writer = csv.writer(summary_file)
            # Define the header fields
            fields = ["infected", "hospitalised", "intensive_care"]
            header = ["time_stamp", "region"]
            for field in fields:
                header.append("current_" + field)
                header.append("daily_" + field)
            header.extend(["daily_hospital_deaths", "daily_deaths"])
            writer.writerow(header)
    
    def _create_config_file(self):
        """Create and initialize the config YAML file."""
        # Only rank 0 or non-MPI runs should create the config file
        if not mpi_available or self.mpi_rank == 0:
            description = {
                "description": f"Started running at {datetime.now()}. Good luck!",
                "mpi_enabled": mpi_available,
                "mpi_size": mpi_size if mpi_available else 1
            }
            with open(self.record_path / self.configs_filename, "w") as f:
                yaml.dump(description, f)

    def static_data(self, world: "World"):
        """
        Record static data about the world.
        
        Parameters
        ----------
        world : World
            The simulation world object
        """
        if not self.record_static_data:
            return
            
        try:
            with tables.open_file(self.record_path / self.filename, mode="a") as file:
                for static_name in self.statics.keys():
                    self.statics[static_name].record(hdf5_file=file, world=world)
                    
            if self.mpi_rank is not None:
                mpi_logger.info(f"Rank {self.mpi_rank}: Successfully recorded static data")
                
        except Exception as e:
            logger.error(f"Error recording static data: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error recording static data: {str(e)}")
                
    def accumulate(self, table_name: str, **kwargs):
        """
        Accumulate event data.
        
        Parameters
        ----------
        table_name : str
            Name of the event table
        **kwargs : 
            Event-specific parameters
        """
        try:
            self.events[table_name].accumulate(**kwargs)
        except Exception as e:
            logger.error(f"Error accumulating data for table {table_name}: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error accumulating data for table {table_name}: {str(e)}")

    def time_step(self, timestamp: str):
        """
        Record events for the current time step.
        Enhanced with MPI synchronization and error handling.
        
        Parameters
        ----------
        timestamp : str
            Current simulation timestamp
        """
        try:
            with tables.open_file(self.record_path / self.filename, mode="a") as file:
                for event_name in self.events.keys():
                    self.events[event_name].record(hdf5_file=file, timestamp=timestamp)
            
            if mpi_available and self.mpi_rank is not None:
                logger.info(f"Rank {self.mpi_rank}: Successfully recorded time step data for {timestamp}")
            else:
                logger.info(f"Successfully recorded time step data for {timestamp}")
                
        except Exception as e:
            logger.error(f"Error in time_step recording: {str(e)}")
            if mpi_available and self.mpi_rank is not None:
                logger.error(f"Rank {self.mpi_rank}: Error in time_step recording: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

    def summarise_hospitalisations(self, world: "World"):
        """
        Summarize hospitalization data.
        Handles case when hospitals are missing in the world.
        
        Parameters
        ----------
        world : World
            The simulation world object
            
        Returns
        -------
        tuple
            (hospital_admissions, icu_admissions, current_hospitalised, current_intensive_care)
        """
        hospital_admissions, icu_admissions = defaultdict(int), defaultdict(int)
        current_hospitalised, current_intensive_care = defaultdict(int), defaultdict(int)
        
        try:
            # Check if hospitals exist in the world
            if not hasattr(world, 'hospitals') or world.hospitals is None:
                logger.warning("No hospitals found in world. Hospitalisation statistics will be empty.")
                return hospital_admissions, icu_admissions, current_hospitalised, current_intensive_care
                
            # Count hospital admissions
            for hospital_id in self.events["hospital_admissions"].hospital_ids:
                try:
                    hospital = world.hospitals.get_from_id(hospital_id)
                    if hospital:
                        hospital_admissions[hospital.region_name] += 1
                except (AttributeError, KeyError):
                    continue
                    
            # Count ICU admissions
            for hospital_id in self.events["icu_admissions"].hospital_ids:
                try:
                    hospital = world.hospitals.get_from_id(hospital_id)
                    if hospital:
                        icu_admissions[hospital.region_name] += 1
                except (AttributeError, KeyError):
                    continue
                    
            # Count current hospitalizations
            for hospital in world.hospitals:
                if not hospital.external:
                    current_hospitalised[hospital.region_name] += len(hospital.ward)
                    current_intensive_care[hospital.region_name] += len(hospital.icu)
                    
            return (
                hospital_admissions,
                icu_admissions,
                current_hospitalised,
                current_intensive_care,
            )
            
        except Exception as e:
            logger.error(f"Error summarizing hospitalizations: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error summarizing hospitalizations: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)

    def summarise_infections(self, world: "World"):
        """
        Summarize infection data.
        
        Parameters
        ----------
        world : World
            The simulation world object
            
        Returns
        -------
        tuple
            (daily_infections, current_infected) - both defaultdicts with region names as keys
        """
        daily_infections, current_infected = defaultdict(int), defaultdict(int)
        
        try:
            # Count daily infections by region
            for region in self.events["infections"].region_names:
                daily_infections[region] += 1
                
            # Count currently infected people by region
            for region in world.regions:
                current_infected[region.name] = len(
                    [person for person in region.people if person.infected]
                )
                
            return daily_infections, current_infected
            
        except Exception as e:
            logger.error(f"Error summarizing infections: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error summarizing infections: {str(e)}")
            return defaultdict(int), defaultdict(int)

    def summarise_deaths(self, world: "World"):
        """
        Summarize death data.
        
        Parameters
        ----------
        world : World
            The simulation world object
            
        Returns
        -------
        tuple
            (daily_deaths, daily_deaths_in_hospital)
        """
        daily_deaths, daily_deaths_in_hospital = defaultdict(int), defaultdict(int)
        
        try:
            for i, person_id in enumerate(self.events["deaths"].dead_person_ids):
                person = world.people.get_from_id(person_id)
                if person and person.super_area and person.super_area.region:
                    region = person.super_area.region.name
                    daily_deaths[region] += 1
                    
                    if self.events["deaths"].location_specs[i] == "hospital":
                        hospital_id = self.events["deaths"].location_ids[i]
                        hospital = world.hospitals.get_from_id(hospital_id)
                        if hospital:
                            daily_deaths_in_hospital[hospital.region_name] += 1
                            
            return daily_deaths, daily_deaths_in_hospital
            
        except Exception as e:
            logger.error(f"Error summarizing deaths: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error summarizing deaths: {str(e)}")
            return defaultdict(int), defaultdict(int)
    
    def get_age_bin(self, age):
        """
        Convert an age to a 5-year bin string.
        
        Parameters
        ----------
        age : int or None
            The age to convert
            
        Returns
        -------
        str
            Age bin string (e.g., "25-29")
        """
        if age is None:
            return "Unknown"
        lower_bound = (age // 5) * 5
        upper_bound = lower_bound + 4
        return f"{lower_bound}-{upper_bound}"

    def get_person_details(self, person_id, world):
        """
        Get demographic details for a person.
        
        Parameters
        ----------
        person_id : int
            ID of the person
        world : World
            The simulation world object
            
        Returns
        -------
        dict
            Person's demographic details
        """
        try:
            # Convert numpy int to standard Python int if needed
            if hasattr(person_id, 'item'):
                person_id = person_id.item()
            else:
                person_id = int(person_id)
                
            # Use find_by_id from Person class which is more robust
            from june.demography.person import Person
            person = Person.find_by_id(person_id)
            
            if not person:
                return {"age": None, "gender": "Unknown", "msoa": "Unknown", "age_bin": "Unknown"}
            
            age = person.age
            msoa = "Unknown"
            if person.area and person.area.super_area:
                msoa = person.area.super_area.name
                
            return {
                "age": age,
                "gender": person.sex,
                "msoa": msoa,
                "age_bin": self.get_age_bin(age)
            }
            
        except Exception as e:
            logger.error(f"Error getting details for person {person_id}: {str(e)}")
            return {"age": None, "gender": "Unknown", "msoa": "Unknown", "age_bin": "Unknown"}
    
    def summarise_by_demographics(self, timestamp, world):
        """
        Create comprehensive demographic summaries for all events.
        
        Parameters
        ----------
        timestamp : datetime
            Current simulation timestamp
        world : World
            The simulation world object
        """
        try:
            # Initialize a multi-dimensional defaultdict to store all metrics
            demographic_data = defaultdict(lambda: defaultdict(int))
            
            # Process infections
            for infected_id in self.events["infections"].infected_ids:
                details = self.get_person_details(infected_id, world)
                key = (details["msoa"], details["gender"], details["age_bin"])
                demographic_data[key]["infections"] += 1
            
            # Process hospital admissions
            for patient_id in self.events["hospital_admissions"].patient_ids:
                details = self.get_person_details(patient_id, world)
                key = (details["msoa"], details["gender"], details["age_bin"])
                demographic_data[key]["hospitalisations"] += 1
            
            # Process ICU admissions
            for patient_id in self.events["icu_admissions"].patient_ids:
                details = self.get_person_details(patient_id, world)
                key = (details["msoa"], details["gender"], details["age_bin"])
                demographic_data[key]["icu_admissions"] += 1
            
            # Process deaths
            for person_id in self.events["deaths"].dead_person_ids:
                details = self.get_person_details(person_id, world)
                key = (details["msoa"], details["gender"], details["age_bin"])
                demographic_data[key]["deaths"] += 1
            
            # Write to detailed demographic summary file
            self.write_demographic_summary(timestamp, demographic_data)
            
        except Exception as e:
            logger.error(f"Error in summarise_by_demographics: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error in summarise_by_demographics: {str(e)}")
                import traceback
                mpi_logger.error(traceback.format_exc())

    def write_demographic_summary(self, timestamp, demographic_data):
        """
        Write the demographic summary to a file.
        
        Parameters
        ----------
        timestamp : datetime
            Current simulation timestamp
        demographic_data : defaultdict
            Demographics data to write
        """
        try:
            # Use rank-specific filename if in MPI mode
            filepath = self.record_path / self.demographic_filename
            
            # Create file with header if it doesn't exist
            file_exists = filepath.exists()
            
            with open(filepath, "a", newline="") as f:
                writer = csv.writer(f)
                
                # Write header if this is a new file
                if not file_exists:
                    writer.writerow([
                        "timestamp", "msoa", "gender", "age_bin", 
                        "infections", "hospitalisations", "icu_admissions", "deaths"
                    ])
                
                # Write data rows
                for key, metrics in demographic_data.items():
                    # Skip entries with no data
                    if not any(metrics.values()):
                        continue
                        
                    area, gender, age_bin = key
                    row = [
                        timestamp.strftime("%Y-%m-%d"),
                        area,
                        gender,
                        age_bin,
                        metrics.get("infections", 0),
                        metrics.get("hospitalisations", 0),
                        metrics.get("icu_admissions", 0),
                        metrics.get("deaths", 0)
                    ]
                    writer.writerow(row)
                    
        except Exception as e:
            logger.error(f"Error writing demographic summary: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error writing demographic summary: {str(e)}")

    def summarise_current_status_by_msoa(self, world):
        """
        Calculate current status metrics by MSOA.
        Handles missing hospitals gracefully.
        
        Parameters
        ----------
        world : World
            The simulation world object
            
        Returns
        -------
        tuple
            (current_infected_by_msoa, current_hospitalised_by_msoa, current_icu_by_msoa)
        """
        try:
            # Initialize dictionaries to store current counts by MSOA
            current_infected_by_msoa = defaultdict(lambda: defaultdict(int))
            current_hospitalised_by_msoa = defaultdict(lambda: defaultdict(int))
            current_icu_by_msoa = defaultdict(lambda: defaultdict(int))
            
            # Count currently infected people by MSOA
            if hasattr(world, 'people') and world.people:
                for person in world.people:
                    if not person.infected:
                        continue
                        
                    # Skip if the person has no area or super_area
                    if not (hasattr(person, 'area') and person.area and 
                            hasattr(person.area, 'super_area') and person.area.super_area):
                        continue
                        
                    msoa = person.area.super_area.name
                    gender = getattr(person, 'sex', 'unknown')
                    age_bin = self.get_age_bin(getattr(person, 'age', None))
                    
                    # Increment the counter for this demographic group
                    current_infected_by_msoa[(msoa, gender, age_bin)]["infections"] += 1
            
            # Count currently hospitalized and ICU patients by MSOA if hospitals exist
            if hasattr(world, 'hospitals') and world.hospitals:
                for hospital in world.hospitals:
                    if hospital.external:
                        continue
                        
                    # Process ward patients (hospitalized)
                    if hasattr(hospital, 'ward') and hospital.ward:
                        for person in hospital.ward.people:
                            if not (hasattr(person, 'area') and person.area and 
                                    hasattr(person.area, 'super_area') and person.area.super_area):
                                continue
                                
                            msoa = person.area.super_area.name
                            gender = getattr(person, 'sex', 'unknown')
                            age_bin = self.get_age_bin(getattr(person, 'age', None))
                            
                            current_hospitalised_by_msoa[(msoa, gender, age_bin)]["hospitalisations"] += 1
                    
                    # Process ICU patients
                    if hasattr(hospital, 'icu') and hospital.icu:
                        for person in hospital.icu.people:
                            if not (hasattr(person, 'area') and person.area and 
                                    hasattr(person.area, 'super_area') and person.area.super_area):
                                continue
                                
                            msoa = person.area.super_area.name
                            gender = getattr(person, 'sex', 'unknown')
                            age_bin = self.get_age_bin(getattr(person, 'age', None))
                            
                            current_icu_by_msoa[(msoa, gender, age_bin)]["icu_admissions"] += 1
            else:
                logger.info("No hospitals found when summarizing by MSOA. Hospital statistics will be empty.")
            
            return current_infected_by_msoa, current_hospitalised_by_msoa, current_icu_by_msoa
            
        except Exception as e:
            logger.error(f"Error summarizing current status by MSOA: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error summarizing current status by MSOA: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))

    def write_current_status_summary(self, timestamp, current_status_data):
        """
        Write current status metrics to a dedicated file.
        
        Parameters
        ----------
        timestamp : datetime
            Current simulation timestamp
        current_status_data : tuple
            (current_infected_by_msoa, current_hospitalised_by_msoa, current_icu_by_msoa)
        """
        try:
            # Use rank-specific filename if in MPI mode
            filepath = self.record_path / self.current_status_filename
            
            # Create file with header if it doesn't exist
            file_exists = filepath.exists()
            
            with open(filepath, "a", newline="") as f:
                writer = csv.writer(f)
                
                # Write header if this is a new file
                if not file_exists:
                    writer.writerow([
                        "timestamp", "msoa", "gender", "age_bin", 
                        "current_infections", "current_hospitalisations", "current_icu"
                    ])
                
                # Combine all data
                all_keys = set()
                all_keys.update(current_status_data[0].keys())
                all_keys.update(current_status_data[1].keys())
                all_keys.update(current_status_data[2].keys())
                
                for key in all_keys:
                    msoa, gender, age_bin = key
                    
                    # Get counts for each metric (defaulting to 0)
                    infections = current_status_data[0].get(key, {}).get("infections", 0)
                    hospitalisations = current_status_data[1].get(key, {}).get("hospitalisations", 0)
                    icu = current_status_data[2].get(key, {}).get("icu_admissions", 0)
                    
                    # Only write non-zero entries
                    if infections > 0 or hospitalisations > 0 or icu > 0:
                        row = [
                            timestamp.strftime("%Y-%m-%d"),
                            msoa,
                            gender,
                            age_bin,
                            infections,
                            hospitalisations,
                            icu
                        ]
                        writer.writerow(row)
                        
        except Exception as e:
            logger.error(f"Error writing current status summary: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error writing current status summary: {str(e)}")

    def summarise_time_step(self, timestamp: str, world: "World"):
        """
        Summarize the current state of the simulation and write to summary files.
        Enhanced with MPI synchronization and error handling.
        Handles missing hospitals and other components gracefully.
        
        Parameters
        ----------
        timestamp : str
            Current simulation timestamp
        world : World
            The simulation world object
        """
        start_time = time.time()
        
        try:
            # Gather local statistics
            daily_infected, current_infected = self.summarise_infections(world=world)
            try:
                (
                    daily_hospitalised,
                    daily_intensive_care,
                    current_hospitalised,
                    current_intensive_care,
                ) = self.summarise_hospitalisations(world=world)
            except Exception as e:
                logger.error(f"Error summarizing hospitalizations: {e}")
                daily_hospitalised = defaultdict(int)
                daily_intensive_care = defaultdict(int)
                current_hospitalised = defaultdict(int)
                current_intensive_care = defaultdict(int)
                
            try:
                daily_deaths, daily_deaths_in_hospital = self.summarise_deaths(world=world)
            except Exception as e:
                logger.error(f"Error summarizing deaths: {e}")
                daily_deaths = defaultdict(int)
                daily_deaths_in_hospital = defaultdict(int)
            
            # Get all region names
            all_regions = set()
            
            # Add regions from world.regions
            try:
                if hasattr(world, 'regions') and world.regions:
                    all_regions.update([region.name for region in world.regions])
            except Exception as e:
                logger.warning(f"Error getting region names from world.regions: {e}")
                
            # Add regions from hospitals if they exist
            try:
                if hasattr(world, 'hospitals') and world.hospitals:
                    all_regions.update([hospital.region_name for hospital in world.hospitals])
            except Exception as e:
                logger.warning(f"Error getting region names from world.hospitals: {e}")
                
            # Add any regions from the statistics dictionaries
            all_regions.update(current_infected.keys())
            all_regions.update(daily_infected.keys())
            all_regions.update(current_hospitalised.keys())
            all_regions.update(daily_hospitalised.keys())
            all_regions.update(current_intensive_care.keys())
            all_regions.update(daily_intensive_care.keys())
            all_regions.update(daily_deaths_in_hospital.keys())
            all_regions.update(daily_deaths.keys())
            
            # If no regions found, create at least one default region
            if not all_regions:
                all_regions = {'default_region'}
                logger.warning("No regions found. Using 'default_region' as fallback.")
            
            # Ensure all ranks have finished gathering their local statistics if using MPI
            if self.mpi_rank is not None:
                mpi_comm.Barrier()
            
            # Write to the summary file
            with open(
                self.record_path / self.summary_filename, "a", newline=""
            ) as summary_file:
                summary_writer = csv.writer(summary_file)
                for region in all_regions:
                    data = [
                        current_infected.get(region, 0),
                        daily_infected.get(region, 0),
                        current_hospitalised.get(region, 0),
                        daily_hospitalised.get(region, 0),
                        current_intensive_care.get(region, 0),
                        daily_intensive_care.get(region, 0),
                        daily_deaths_in_hospital.get(region, 0),
                        daily_deaths.get(region, 0),
                    ]
                    if sum(data) > 0:
                        summary_writer.writerow(
                            [timestamp.strftime("%Y-%m-%d"), region] + data
                        )
            
            # Write demographic summaries (each rank writes its own data)
            try:
                self.summarise_by_demographics(timestamp, world)
            except Exception as e:
                logger.error(f"Error summarizing by demographics: {e}")
            
            # Calculate and write current status by MSOA
            try:
                current_infected_by_msoa, current_hospitalised_by_msoa, current_icu_by_msoa = \
                    self.summarise_current_status_by_msoa(world)
                
                self.write_current_status_summary(
                    timestamp, 
                    (current_infected_by_msoa, current_hospitalised_by_msoa, current_icu_by_msoa)
                )
            except Exception as e:
                logger.error(f"Error summarizing current status by MSOA: {e}")
            
            # Log successful completion on this rank
            end_time = time.time()
            if self.mpi_rank is not None:
                mpi_logger.info(
                    f"Rank {self.mpi_rank}: Successfully summarized time step for {timestamp} "
                    f"in {end_time - start_time:.2f} seconds"
                )
        
        except Exception as e:
            # Log the error but don't crash the simulation
            logger.error(f"Error in summarise_time_step: {str(e)}")
            if self.mpi_rank is not None:
                mpi_logger.error(f"Rank {self.mpi_rank}: Error in summarise_time_step: {str(e)}")
                import traceback
                mpi_logger.error(traceback.format_exc())

    def _combine_demographic_files(self, remove_left_overs=False):
        """
        Combine demographic and current status files from all ranks.
        
        Parameters
        ----------
        remove_left_overs : bool, optional
            Whether to remove individual rank files after combining
        """
        try:
            # Find demographic files
            demographic_files = list(self.record_path.glob(f"detailed_demographic_summary.*.csv"))
            status_files = list(self.record_path.glob(f"current_status_by_msoa.*.csv"))
            
            # Process demographic files
            if demographic_files:
                logger.info(f"Combining {len(demographic_files)} demographic files...")
                combined_demographic = self._process_csv_files(demographic_files)
                if combined_demographic is not None:
                    # Group by all dimensions and sum the metrics
                    # This ensures we don't lose any MSOA data
                    group_cols = ['timestamp', 'msoa', 'gender', 'age_bin']
                    metric_cols = ['infections', 'hospitalisations', 'icu_admissions', 'deaths']
                    combined_demographic = combined_demographic.groupby(group_cols)[metric_cols].sum().reset_index()
                    combined_demographic.to_csv(
                        self.record_path / "detailed_demographic_summary.csv", 
                        index=False
                    )
                    
                    # Remove originals if requested
                    if remove_left_overs:
                        for file_path in demographic_files:
                            try:
                                file_path.unlink()
                            except Exception as e:
                                logger.warning(f"Failed to remove {file_path}: {str(e)}")
                
                # Process status files
                if status_files:
                    logger.info(f"Combining {len(status_files)} current status files...")
                    combined_status = self._process_csv_files(status_files)
                    if combined_status is not None:
                        # Similarly group by dimensions and sum metrics for status files
                        status_group_cols = ['timestamp', 'msoa', 'gender', 'age_bin']
                        status_metric_cols = ['current_infections', 'current_hospitalisations', 'current_icu']
                        combined_status = combined_status.groupby(status_group_cols)[status_metric_cols].sum().reset_index()
                        combined_status.to_csv(
                            self.record_path / "current_status_by_msoa.csv", 
                            index=False
                        )
                    
                    # Remove originals if requested
                    if remove_left_overs:
                        for file_path in status_files:
                            try:
                                file_path.unlink()
                            except Exception as e:
                                logger.warning(f"Failed to remove {file_path}: {str(e)}")
                                
        except Exception as e:
            logger.error(f"Error combining demographic files: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _process_csv_files(self, file_list):
        """
        Process and combine CSV files.
        
        Parameters
        ----------
        file_list : list
            List of Path objects pointing to CSV files
            
        Returns
        -------
        pandas.DataFrame or None
            Combined DataFrame or None if no valid data found
        """
        dfs = []
        for file_path in file_list:
            try:
                df = pd.read_csv(file_path)
                if len(df) > 0:
                    dfs.append(df)
            except Exception as e:
                logger.error(f"Error reading {file_path}: {str(e)}")
                
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        else:
            return None
        
    def append_dict_to_configs(self, config_dict):
        with open(self.record_path / self.configs_filename, "r") as f:
            configs = yaml.safe_load(f)
            configs.update(config_dict)
        with open(self.record_path / self.configs_filename, "w") as f:
            yaml.safe_dump(
                configs,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    def parameters_interaction(self, interaction: "Interaction" = None):
        if interaction is not None:
            interaction_dict = {}
            interaction_dict["betas"] = interaction.betas
            interaction_dict["alpha_physical"] = interaction.alpha_physical
            interaction_dict["contact_matrices"] = {}
            for key, values in interaction.contact_matrices.items():
                interaction_dict["contact_matrices"][key] = values.tolist()
            self.append_dict_to_configs(config_dict={"interaction": interaction_dict})

    def parameters_seed(self, infection_seeds: "InfectionSeeds" = None):
        if infection_seeds is not None:
            infection_seeds_dict = {}
            for infection_seed in infection_seeds:
                inf_seed_dict = {}
                inf_seed_dict["seed_strength"] = infection_seed.seed_strength
                inf_seed_dict["min_date"] = infection_seed.min_date.strftime("%Y-%m-%d")
                inf_seed_dict["max_date"] = infection_seed.max_date.strftime("%Y-%m-%d")
                infection_seeds_dict[
                    infection_seed.infection_selector.infection_class.__name__
                ] = inf_seed_dict
            self.append_dict_to_configs(
                config_dict={"infection_seeds": infection_seeds_dict}
            )

    def parameters_infection(self, infection_selectors: "InfectionSelectors" = None):
        if infection_selectors is not None:
            save_dict = {}
            for selector in infection_selectors._infection_selectors:
                class_name = selector.infection_class.__name__
                save_dict[class_name] = {}
                save_dict[class_name]["transmission_type"] = selector.transmission_type
            self.append_dict_to_configs(config_dict={"infections": save_dict})

    def parameters_policies(self, activity_manager: "ActivityManager" = None):
        if activity_manager is not None and activity_manager.policies is not None:
            policy_dicts = []
            for policy in activity_manager.policies.policies:
                policy_dicts.append(policy.__dict__.copy())
            with open(self.record_path / "policies.json", "w") as f:
                json.dump(policy_dicts, f, indent=4, default=str)

    @staticmethod
    def get_username():
        try:
            username = os.getlogin()
        except Exception:
            username = "no_user"
        return username

    def parameters(
        self,
        interaction: "Interaction" = None,
        epidemiology: "Epidemiology" = None,
        activity_manager: "ActivityManager" = None,
    ):
        try:
            if epidemiology:
                infection_seeds = epidemiology.infection_seeds
                infection_selectors = epidemiology.infection_selectors
            if not mpi_available or self.mpi_rank == 0:
                self.parameters_interaction(interaction=interaction)
                self.parameters_seed(infection_seeds=infection_seeds)
                self.parameters_infection(infection_selectors=infection_selectors)
                # Only try to record policies if they exist
                if activity_manager is not None and activity_manager.policies is not None:
                    self.parameters_policies(activity_manager=activity_manager)
        except Exception as e:
            logger.error(f"Error recording parameters: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def meta_information(
        self,
        comment: Optional[str] = None,
        random_state: Optional[int] = None,
        number_of_cores: Optional[int] = None,
    ):
        if not mpi_available or self.mpi_rank == 0:
            june_git = Path(june.__path__[0]).parent / ".git"
            meta_dict = {}
            branch_cmd = f"git --git-dir {june_git} rev-parse --abbrev-ref HEAD".split()
            try:
                meta_dict["branch"] = (
                    subprocess.run(branch_cmd, stdout=subprocess.PIPE)
                    .stdout.decode("utf-8")
                    .strip()
                )
            except Exception as e:
                print(e)
                print("Could not record git branch")
                meta_dict["branch"] = "unavailable"
            local_SHA_cmd = f'git --git-dir {june_git} log -n 1 --format="%h"'.split()
            try:
                meta_dict["local_SHA"] = (
                    subprocess.run(local_SHA_cmd, stdout=subprocess.PIPE)
                    .stdout.decode("utf-8")
                    .strip()
                )
            except Exception:
                print("Could not record local git SHA")
                meta_dict["local_SHA"] = "unavailable"
            user = self.get_username()
            meta_dict["user"] = user
            if comment is None:
                comment = "No comment provided."
            meta_dict["user_comment"] = f"{comment}"
            meta_dict["june_path"] = str(june.__path__[0])
            meta_dict["number_of_cores"] = number_of_cores
            meta_dict["random_state"] = random_state
            with open(self.record_path / self.configs_filename, "r") as f:
                configs = yaml.safe_load(f)
                configs.update({"meta_information": meta_dict})
            with open(self.record_path / self.configs_filename, "w") as f:
                yaml.safe_dump(configs, f)
            
    def combine_outputs(self, remove_left_overs=False):
        """
        Combine outputs from all MPI ranks into consolidated files.
        Enhanced with better error handling and synchronization.
        
        Parameters
        ----------
        remove_left_overs : bool, optional
            Whether to remove individual rank files after combining
        """
        # Only perform the combine if using MPI with multiple processes
        if not mpi_available or mpi_size <= 1:
            logger.info("Not using MPI or single process, no need to combine outputs.")
            return
            
        # Ensure all ranks have finished writing their files
        mpi_comm.Barrier()
        
        try:
            # Only rank 0 performs the combining
            if self.mpi_rank == 0:
                logger.info("Starting to combine outputs from all ranks...")
                combine_records(self.record_path, remove_left_overs=remove_left_overs)
                # Additionally combine demographic and status files
                self._combine_demographic_files(remove_left_overs=remove_left_overs)
                logger.info("Successfully combined outputs from all ranks.")
            
            # Wait for rank 0 to finish combining
            mpi_comm.Barrier()
            
            # If removing left-overs, each rank should clean up its own files
            if remove_left_overs and self.mpi_rank != 0:
                try:
                    # Remove this rank's HDF5 and summary files
                    rank_hdf5 = self.record_path / self.filename
                    rank_summary = self.record_path / self.summary_filename
                    rank_demographic = self.record_path / self.demographic_filename
                    rank_status = self.record_path / self.current_status_filename
                    
                    for filepath in [rank_hdf5, rank_summary, rank_demographic, rank_status]:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            
                    logger.info(f"Rank {self.mpi_rank}: Removed rank-specific files.")
                except Exception as e:
                    logger.warning(f"Rank {self.mpi_rank}: Failed to remove files: {str(e)}")
        
        except Exception as e:
            logger.error(f"Rank {self.mpi_rank}: Error in combine_outputs: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Final synchronization point
        mpi_comm.Barrier()

def combine_records(record_path, remove_left_overs=False, save_dir=None):
    """
    Combined wrapper function for combining HDF5 and summary files from all MPI ranks.
    
    Parameters
    ----------
    record_path : str or Path
        Path to the directory containing record files
    remove_left_overs : bool, optional
        Whether to remove individual rank files after combining
    save_dir : str or Path, optional
        Directory to save the combined files
    """
    # Skip if not using MPI or only one process
    if not mpi_available or mpi_size <= 1:
        logger.info("Not using MPI or single process, no need to combine records.")
        return
    
    # Log start of combine process
    logger.info(f"Starting combine_records for path: {record_path}")
    
    try:
        record_path = Path(record_path)
        
        # First combine summary files
        logger.info("Combining summary files...")
        combine_summaries(
            record_path, remove_left_overs=remove_left_overs, save_dir=save_dir
        )
        
        # Then combine HDF5 files
        logger.info("Combining HDF5 files...")
        combine_hdf5s(record_path, remove_left_overs=remove_left_overs, save_dir=save_dir)
        
        # Also combine demographic summaries and current status files
        logger.info("Combining demographic and status files...")
        demographic_files = list(record_path.glob("detailed_demographic_summary.*.csv"))
        status_files = list(record_path.glob("current_status_by_msoa.*.csv"))
        
        if demographic_files:
            logger.info(f"Found {len(demographic_files)} demographic files to combine")
            try:
                dfs = []
                for file_path in demographic_files:
                    try:
                        df = pd.read_csv(file_path)
                        if len(df) > 0:
                            dfs.append(df)
                        
                        if remove_left_overs:
                            file_path.unlink()
                            logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error processing demographic file {file_path}: {str(e)}")
                
                if dfs:
                    combined_demographic = pd.concat(dfs, ignore_index=True)
                    save_path = Path(save_dir) if save_dir else record_path
                    combined_demographic.to_csv(save_path / "detailed_demographic_summary.csv", index=False)
                    logger.info("Successfully combined demographic files")
            except Exception as e:
                logger.error(f"Error combining demographic files: {str(e)}")
        
        if status_files:
            logger.info(f"Found {len(status_files)} status files to combine")
            try:
                dfs = []
                for file_path in status_files:
                    try:
                        df = pd.read_csv(file_path)
                        if len(df) > 0:
                            dfs.append(df)
                        
                        if remove_left_overs:
                            file_path.unlink()
                            logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error processing status file {file_path}: {str(e)}")
                
                if dfs:
                    combined_status = pd.concat(dfs, ignore_index=True)
                    save_path = Path(save_dir) if save_dir else record_path
                    combined_status.to_csv(save_path / "current_status_by_msoa.csv", index=False)
                    logger.info("Successfully combined status files")
            except Exception as e:
                logger.error(f"Error combining status files: {str(e)}")
        
        logger.info("Successfully completed combine_records")
        
    except Exception as e:
        logger.error(f"Error in combine_records: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def combine_summaries(record_path, remove_left_overs=False, save_dir=None):
    """
    Combine summary files from all MPI ranks.
    Enhanced with better error handling and optimized for MPI environments.
    
    Parameters
    ----------
    record_path : str or Path
        Path to the directory containing summary files
    remove_left_overs : bool, optional
        Whether to remove individual rank files after combining
    save_dir : str or Path, optional
        Directory to save the combined summary
    """
    try:
        record_path = Path(record_path)
        logger.info(f"Combining summary files from {record_path}...")
        
        # Find all summary files
        summary_files = list(record_path.glob("summary.*.csv"))
        logger.info(f"Found {len(summary_files)} summary files to combine.")
        
        if not summary_files:
            logger.warning("No summary files found to combine.")
            return
        
        # Read and process files
        dfs = []
        for summary_file in summary_files:
            try:
                df = pd.read_csv(summary_file)
                if len(df) == 0:
                    logger.info(f"Skipping empty summary file: {summary_file}")
                    continue
                
                # Create aggregation dictionary - use strings for aggregation methods
                aggregator = {
                    col: 'mean' if 'current' in col else 'sum' 
                    for col in df.columns[2:]
                }
                
                # Group by region and timestamp
                df = df.groupby(['region', 'time_stamp'], as_index=False).agg(aggregator)
                dfs.append(df)
                
                # Remove original file if requested
                if remove_left_overs:
                    try:
                        summary_file.unlink()
                        logger.info(f"Removed summary file: {summary_file}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {summary_file}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error processing summary file {summary_file}: {str(e)}")
        
        if not dfs:
            logger.warning("No valid summary data found to combine!")
            return
        
        # Combine all summaries
        logger.info("Concatenating and aggregating summary data...")
        summary = pd.concat(dfs)
        summary = summary.groupby(["region", "time_stamp"]).sum().reset_index()
        
        # Create a total row
        try:
            logger.info("Creating total summary row...")
            
            # Get the last timestamp for the total row
            last_timestamp = summary['time_stamp'].max()
            
            # Initialize total row
            total_row = {'time_stamp': last_timestamp, 'region': 'TOTAL'}
            
            # Calculate totals for each column
            for col in summary.columns[2:]:  # Skip time_stamp and region
                if 'current' in col:
                    # For 'current' columns, take the mean of non-zero values from the last timestamp
                    last_day_data = summary[summary['time_stamp'] == last_timestamp]
                    non_zero_values = last_day_data[col][last_day_data[col] > 0]
                    total_row[col] = non_zero_values.mean() if len(non_zero_values) > 0 else 0
                else:
                    # For 'daily' columns, sum all values across all time periods
                    total_row[col] = summary[col].sum()
            
            # Add total row to the summary
            summary = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)
            
        except Exception as e:
            logger.error(f"Error creating total summary row: {str(e)}")
        
        # Save the combined summary
        if save_dir is None:
            save_path = record_path
        else:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
        
        full_summary_save_path = save_path / "summary.csv"
        logger.info(f"Saving combined summary to {full_summary_save_path}")
        summary.to_csv(full_summary_save_path, index=False)
        logger.info("Successfully combined summary files.")
        
    except Exception as e:
        logger.error(f"Error in combine_summaries: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def combine_hdf5s(
    record_path,
    table_names=("infections", "population"),
    remove_left_overs=False,
    save_dir=None,
):
    """
    Combine HDF5 files from all MPI ranks.
    Enhanced with better error handling and processing.
    
    Parameters
    ----------
    record_path : str or Path
        Path to the directory containing HDF5 files
    table_names : tuple, optional
        Names of tables to include
    remove_left_overs : bool, optional
        Whether to remove individual rank files after combining
    save_dir : str or Path, optional
        Directory to save the combined HDF5 file
    """

    # Skip if not using MPI or only one process
    if not mpi_available or mpi_size <= 1:
        logger.info("Not using MPI or single process, no need to combine HDF5 files.")
        return
    try:
        # Setup paths
        record_path = Path(record_path)
        if save_dir is None:
            save_path = record_path
        else:
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
        full_record_save_path = save_path / "june_record.h5"
        logger.info(f"Combining HDF5 files to {full_record_save_path}")
        
        # Find all rank files using pattern matching
        rank_files = list(record_path.glob("june_record.*.h5"))
        rank_files = [str(f) for f in rank_files]  # Convert Path objects to strings
        
        logger.info(f"Found {len(rank_files)} rank HDF5 files to combine.")
        
        if not rank_files:
            logger.warning("No rank HDF5 files found to combine.")
            return
        
        # Create the output file
        with tables.open_file(str(full_record_save_path), "w") as merged_record:
            # Process each rank's file
            for rank_file in rank_files:
                try:
                    with tables.open_file(rank_file, "r") as temp_file:
                        # Process each node in the file
                        for node in temp_file.root:
                            try:
                                # Check if node already exists in merged file
                                node_name = node._v_name
                                if hasattr(merged_record.root, node_name):
                                    # If node already exists, append data
                                    existing_node = getattr(merged_record.root, node_name)
                                    existing_node.append(node[:])
                                    existing_node.flush()
                                else:
                                    # If node doesn't exist, copy it
                                    node._f_copy(merged_record.root, recursive=True)
                            except Exception as e:
                                logger.error(f"Error processing node {node._v_name} in file {rank_file}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing HDF5 file {rank_file}: {str(e)}")
                    
        # Clean up temp files if requested
        if remove_left_overs:
            for rank_file in rank_files:
                try:
                    os.remove(rank_file)
                    logger.info(f"Removed HDF5 file: {rank_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove {rank_file}: {str(e)}")
                    
        logger.info("Successfully combined HDF5 files.")
        
    except Exception as e:
        logger.error(f"Error combining HDF5 files: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def prepend_checkpoint_hdf5(
    pre_checkpoint_record_path,
    post_checkpoint_record_path,
    tables_to_merge=(
        "deaths",
        "discharges",
        "hospital_admissions",
        "icu_admissions",
        "infections",
        "recoveries",
        "symptoms",
    ),
    merged_record_path=None,
    checkpoint_date: str = None,
):
    pre_checkpoint_record_path = Path(pre_checkpoint_record_path)
    post_checkpoint_record_path = Path(post_checkpoint_record_path)
    if merged_record_path is None:
        merged_record_path = (
            post_checkpoint_record_path.parent / "merged_checkpoint_june_record.h5"
        )

    with tables.open_file(merged_record_path, "w") as merged_record:
        with tables.open_file(pre_checkpoint_record_path, "r") as pre_record:
            with tables.open_file(post_checkpoint_record_path, "r") as post_record:
                post_infection_dates = np.array(
                    [
                        datetime.strptime(x.decode("utf-8"), "%Y-%m-%d")
                        for x in post_record.root["infections"][:]["timestamp"]
                    ]
                )
                min_date = min(post_infection_dates)
                if checkpoint_date is None:
                    print("provide the date you expect the checkpoint to start at!")
                else:
                    if checkpoint_date != checkpoint_date:
                        print(
                            f"provided date {checkpoint_date} does not match min date {min_date}"
                        )

                for dataset in post_record.root._f_list_nodes():
                    description = getattr(post_record.root, dataset.name).description
                    if dataset.name not in tables_to_merge:
                        arr_data = dataset[:]
                        merged_record.create_table(
                            merged_record.root, dataset.name, description=description
                        )
                        if len(arr_data) > 0:
                            table = getattr(merged_record.root, dataset.name)
                            table.append(arr_data)
                            table.flush()
                    else:
                        pre_arr_data = pre_record.root[dataset.name][:]
                        pre_dates = np.array(
                            [
                                datetime.strptime(x.decode("utf-8"), "%Y-%m-%d")
                                for x in pre_arr_data["timestamp"]
                            ]
                        )
                        pre_arr_data = pre_arr_data[pre_dates < min_date]
                        post_arr_data = dataset[:]

                        merged_record.create_table(
                            merged_record.root, dataset.name, description=description
                        )
                        table = getattr(merged_record.root, dataset.name)
                        if len(pre_arr_data) > 0:
                            table.append(pre_arr_data)
                        if len(post_arr_data) > 0:
                            table.append(post_arr_data)
                        table.flush()
    logger.info(f"written prepended record to {merged_record_path}")


def prepend_checkpoint_summary(
    pre_checkpoint_summary_path,
    post_checkpoint_summary_path,
    merged_summary_path=None,
    checkpoint_date=None,
):
    pre_checkpoint_summary_path = Path(pre_checkpoint_summary_path)
    post_checkpoint_summary_path = Path(post_checkpoint_summary_path)

    if merged_summary_path is None:
        merged_summary_path = (
            post_checkpoint_summary_path.parent / "merged_checkpoint_summary.csv"
        )

    pre_summary = pd.read_csv(pre_checkpoint_summary_path)
    post_summary = pd.read_csv(post_checkpoint_summary_path)
    pre_summary["time_stamp"] = pd.to_datetime(pre_summary["time_stamp"])
    post_summary["time_stamp"] = pd.to_datetime(post_summary["time_stamp"])
    min_date = min(post_summary["time_stamp"])
    if checkpoint_date is None:
        print("Provide the checkpoint date you expect the post-summary to start at!")
    else:
        if min_date != checkpoint_date:
            print(
                f"Provided date {checkpoint_date} does not match the earliest date in the summary!"
            )
    pre_summary = pre_summary[pre_summary["time_stamp"] < min_date]
    merged_summary = pd.concat([pre_summary, post_summary], ignore_index=True)
    merged_summary.set_index(["region", "time_stamp"])
    merged_summary.sort_index(inplace=True)
    merged_summary.to_csv(merged_summary_path, index=True)
    logger.info(f"Written merged summary to {merged_summary_path}")