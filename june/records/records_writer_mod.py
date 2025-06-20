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

import june
from june.demography.person import Person
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

logger = logging.getLogger("records_writer")


class Record:
    def __init__(
        self, record_path: str, record_static_data=False, mpi_rank: Optional[int] = None
    ):
        self.record_path = Path(record_path)
        self.record_path.mkdir(parents=True, exist_ok=True)
        self.mpi_rank = mpi_rank
        if mpi_rank is not None:
            self.filename = f"june_record.{mpi_rank}.h5"
            self.summary_filename = f"summary.{mpi_rank}.csv"
        else:
            self.filename = "june_record.h5"
            self.summary_filename = "summary.csv"
        self.configs_filename = "config.yaml"
        self.record_static_data = record_static_data
        try:
            os.remove(self.record_path / self.filename)
        except OSError:
            pass
        filename = self.record_path / self.filename
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
        if self.record_static_data:
            self.statics = {
                "people": PeopleRecord(),
                "locations": LocationRecord(),
                "areas": AreaRecord(),
                "super_areas": SuperAreaRecord(),
                "regions": RegionRecord(),
            }
        with open(
            self.record_path / self.summary_filename, "w", newline=""
        ) as summary_file:
            writer = csv.writer(summary_file)
            # fields = ["infected", "recovered", "hospitalised", "intensive_care"]
            fields = ["infected", "hospitalised", "intensive_care"]
            header = ["time_stamp", "region"]
            for field in fields:
                header.append("current_" + field)
                header.append("daily_" + field)
            header.extend(
                # ["current_susceptible", "daily_hospital_deaths", "daily_deaths"]
                ["daily_hospital_deaths", "daily_deaths"]
            )
            writer.writerow(header)
        description = {
            "description": f"Started runnning at {datetime.now()}. Good luck!"
        }
        with open(self.record_path / self.configs_filename, "w") as f:
            yaml.dump(description, f)

    def static_data(self, world: "World"):
        with tables.open_file(self.record_path / self.filename, mode="a") as file:
            for static_name in self.statics.keys():
                self.statics[static_name].record(hdf5_file=file, world=world)

    def accumulate(self, table_name: str, **kwargs):
        self.events[table_name].accumulate(**kwargs)

    def time_step(self, timestamp: str):
        with tables.open_file(self.record_path / self.filename, mode="a") as file:
            for event_name in self.events.keys():
                self.events[event_name].record(hdf5_file=file, timestamp=timestamp)


    from collections import defaultdict

    def summarise_hospitalisations(self, world: "World"):
        """
        Summarises hospitalisation data by region, area, sex, and age group.
        """
        # Initialise dictionaries
        hospital_admissions = defaultdict(int)
        icu_admissions = defaultdict(int)
        hospital_admissions_by_area = defaultdict(int)
        icu_admissions_by_area = defaultdict(int)
        current_hospitalised = defaultdict(int)
        current_intensive_care = defaultdict(int)
        current_hospitalised_by_area = defaultdict(int)
        current_intensive_care_by_area = defaultdict(int)

        # Track unique patient IDs currently hospitalised
        hospitalised_person_ids = set()
        intensive_care_person_ids = set()
        
        # Track problematic IDs for debugging
        missing_or_dead_ids = []

        # 1) Summarise hospital admissions & ICU admissions
        for event_type, admissions_dict, admissions_by_area_dict in [
            ("hospital_admissions", hospital_admissions, hospital_admissions_by_area),
            ("icu_admissions", icu_admissions, icu_admissions_by_area)
        ]:
            for person_id, hospital_id in zip(
                self.events[event_type].patient_ids,
                self.events[event_type].hospital_ids
            ):
                try:
                    # Convert to standard Python int if needed
                    person_id = int(person_id.item()) if hasattr(person_id, 'item') else int(person_id)
                    hospital_id = int(hospital_id.item()) if hasattr(hospital_id, 'item') else int(hospital_id)
                    
                    person = Person.find_by_id(person_id)  # Use direct class method
                    if person is None or person.dead:
                        if person is None:
                            missing_or_dead_ids.append(f"{person_id} (missing)")
                        else:
                            missing_or_dead_ids.append(f"{person_id} (dead)")
                        continue
                        
                    hospital = world.hospitals.get_from_id(hospital_id)
                    if hospital is None:
                        continue

                    region = hospital.region_name
                    sex = person.sex
                    age_group = get_age_group(person.age)
                    area = person.area
                    super_area = area.super_area.name

                    # Update both region-level and area-level admissions
                    admissions_dict[(region, sex, age_group)] += 1
                    admissions_by_area_dict[super_area, sex, age_group] += 1
                except (KeyError, AttributeError) as e:
                    logger.warning(f"Error processing patient ID {person_id} in {event_type}: {str(e)}")
                    continue

        # 2) Summarise current hospitalised & ICU patients
        for hospital in world.hospitals:
            if not hospital.external:
                # Create a safe copy of the IDs to allow for removing bad IDs
                ward_ids_to_remove = []
                
                for person_id in hospital.ward_ids:
                    try:
                        person_id = int(person_id.item()) if hasattr(person_id, 'item') else int(person_id)
                        
                        person = Person.find_by_id(person_id)  # Use direct class method
                        if person is None or person.dead:
                            ward_ids_to_remove.append(person_id)
                            if person is None:
                                missing_or_dead_ids.append(f"{person_id} (missing from ward)")
                            else:
                                missing_or_dead_ids.append(f"{person_id} (dead in ward)")
                            continue
                            
                        region = hospital.region_name
                        sex = person.sex
                        age_group = get_age_group(person.age)
                        area = person.area
                        super_area = area.super_area.name

                        current_hospitalised[(region, sex, age_group)] += 1
                        current_hospitalised_by_area[super_area, sex, age_group] += 1
                        hospitalised_person_ids.add(person_id)
                    except (KeyError, AttributeError) as e:
                        logger.warning(f"Error processing ward patient ID {person_id}: {str(e)}")
                        ward_ids_to_remove.append(person_id)
                        continue
                
                # Clean up invalid IDs from the hospital ward list
                for bad_id in ward_ids_to_remove:
                    if bad_id in hospital.ward_ids:  # Check again as IDs might be objects not ints
                        hospital.ward_ids.remove(bad_id)
                
                # Same process for ICU patients
                icu_ids_to_remove = []
                
                for person_id in hospital.icu_ids:
                    try:
                        person_id = int(person_id.item()) if hasattr(person_id, 'item') else int(person_id)
                        
                        person = Person.find_by_id(person_id)  # Use direct class method
                        if person is None or person.dead:
                            icu_ids_to_remove.append(person_id)
                            if person is None:
                                missing_or_dead_ids.append(f"{person_id} (missing from ICU)")
                            else:
                                missing_or_dead_ids.append(f"{person_id} (dead in ICU)")
                            continue
                            
                        region = hospital.region_name
                        sex = person.sex
                        age_group = get_age_group(person.age)
                        area = person.area
                        super_area = area.super_area.name

                        current_intensive_care[(region, sex, age_group)] += 1
                        current_intensive_care_by_area[super_area, sex, age_group] += 1
                        intensive_care_person_ids.add(person_id)
                    except (KeyError, AttributeError) as e:
                        logger.warning(f"Error processing ICU patient ID {person_id}: {str(e)}")
                        icu_ids_to_remove.append(person_id)
                        continue
                
                # Clean up invalid IDs from the hospital ICU list
                for bad_id in icu_ids_to_remove:
                    if bad_id in hospital.icu_ids:  # Check again as IDs might be objects not ints
                        hospital.icu_ids.remove(bad_id)

        # Log summary of issues
        if missing_or_dead_ids:
            logger.warning(f"Found {len(missing_or_dead_ids)} missing or dead persons in hospital records")
            if len(missing_or_dead_ids) <= 20:  # Log more with detailed status
                logger.warning(f"Problem IDs: {', '.join(missing_or_dead_ids)}")

        return (
            hospital_admissions,
            icu_admissions,
            current_hospitalised,
            current_intensive_care,
            current_hospitalised_by_area,
            current_intensive_care_by_area,
            hospital_admissions_by_area,
            icu_admissions_by_area
        )
    """def summarise_hospitalisations(self, world: "World"):
        hospital_admissions, icu_admissions = defaultdict(int), defaultdict(int)
        for hospital_id in self.events["hospital_admissions"].hospital_ids:
            hospital = world.hospitals.get_from_id(hospital_id)
            hospital_admissions[hospital.region_name] += 1
        for hospital_id in self.events["icu_admissions"].hospital_ids:
            hospital = world.hospitals.get_from_id(hospital_id)
            icu_admissions[hospital.region_name] += 1
        current_hospitalised, current_intensive_care = (
            defaultdict(int),
            defaultdict(int),
        )
        for hospital in world.hospitals:
            if not hospital.external:
                current_hospitalised[hospital.region_name] += len(hospital.ward)
                current_intensive_care[hospital.region_name] += len(hospital.icu)
        return (
            hospital_admissions,
            icu_admissions,
            current_hospitalised,
            current_intensive_care,
        )"""


    def summarise_infections(self, world="World"):
        """
        Summarises infection data by region, area, sex, and age group.

        Returns:
            - daily_infections: Daily infections by (region, sex, age_group)
            - current_infected: Current infections by (region, sex, age_group)
            - daily_infections_by_area: Daily infections by residential area
            - current_infected_by_area: Current infections by residential area
        """
        # Initialise dictionaries
        daily_infections = defaultdict(int)
        current_infected = defaultdict(int)
        daily_infections_by_area = defaultdict(int)
        current_infected_by_area = defaultdict(int)
        
        # Track problematic IDs for debugging
        missing_ids = []

        # 1) Summarise daily infections
        for infected_id in self.events["infections"].infected_ids:
            try:
                # Convert numpy int64 to standard Python int if needed
                if hasattr(infected_id, 'item'):
                    infected_id = int(infected_id.item())
                else:
                    infected_id = int(infected_id)
                    
                person = world.people.get_from_id(infected_id)
                if person is None:
                    missing_ids.append(infected_id)
                    continue
                    
                region = person.super_area.region.name
                sex = person.sex
                age_group = get_age_group(person.age)
                area = person.area
                super_area = area.super_area.name

                daily_infections[(region, sex, age_group)] += 1
                daily_infections_by_area[super_area, sex, age_group] += 1
            except (KeyError, AttributeError) as e:
                # Log the error but continue processing
                logger.warning(f"Error processing infected person ID {infected_id}: {e}")
                missing_ids.append(infected_id)
                continue

        # 2) Summarise currently infected cases
        for region in world.regions:
            for person in region.people:
                if person.infected:
                    region_name = region.name
                    sex = person.sex
                    age_group = get_age_group(person.age)
                    area = person.area
                    super_area = area.super_area.name

                    current_infected[(region_name, sex, age_group)] += 1
                    current_infected_by_area[super_area, sex, age_group] += 1

        # Log summary of missing IDs if any were found
        if missing_ids:
            logger.warning(f"Found {len(missing_ids)} missing person IDs in infection records")
            if len(missing_ids) <= 10:  # Only log if there aren't too many
                logger.warning(f"Missing IDs: {missing_ids}")
            
        return (
            daily_infections,
            current_infected,
            daily_infections_by_area,
            current_infected_by_area
        )

    """     
    def summarise_infections(self, world="World"):
        daily_infections, current_infected = defaultdict(int), defaultdict(int)
        for region in self.events["infections"].region_names:
            daily_infections[region] += 1
        for region in world.regions:
            current_infected[region.name] = len(
                [person for person in region.people if person.infected]
            )
        return daily_infections, current_infected """


    def summarise_deaths(self, world="World"):
        """
        Summarises death data by region, area, sex, and age group.
        
        Returns:
            - daily_deaths: Deaths by (region, sex, age_group)
            - daily_deaths_in_hospital: Deaths in hospitals by (person's super area, sex, age_group)
            - daily_deaths_by_area: Deaths by residential area
            - daily_deaths_in_hospital_by_area: Deaths in hospitals by deceased person's residential area
        """

        # Initialise dictionaries
        daily_deaths = defaultdict(int)
        daily_deaths_in_hospital = defaultdict(int)
        daily_deaths_by_area = defaultdict(int)
        daily_deaths_in_hospital_by_area = defaultdict(int)
        
        # Track problematic IDs for debugging
        missing_ids = []

        # Loop through death events
        for i, person_id in enumerate(self.events["deaths"].dead_person_ids):
            try:
                # Convert numpy int64 to standard Python int if needed
                person_id = int(person_id.item()) if hasattr(person_id, 'item') else int(person_id)
                
                # Use Person.find_by_id directly instead of going through world.people
                person = Person.find_by_id(person_id)
                if person is None:
                    missing_ids.append(f"{person_id} (missing)")
                    continue
                    
                # Even if they're marked as dead, we can still record their death stats
                # since this is recording historical deaths
                
                try:
                    region = person.super_area.region.name
                    area = person.area
                    super_area = area.super_area.name
                    sex = person.sex
                    age_group = get_age_group(person.age)

                    # Register deaths in their home region/area
                    daily_deaths[(region, sex, age_group)] += 1
                    daily_deaths_by_area[super_area, sex, age_group] += 1

                    # If the death happened in a hospital, register it under the deceased person's super area
                    if self.events["deaths"].location_specs[i] == "hospital":
                        try:
                            hospital_id = self.events["deaths"].location_ids[i]
                            hospital_id = int(hospital_id.item()) if hasattr(hospital_id, 'item') else int(hospital_id)
                            
                            # Verify the hospital exists - though we don't need it for statistics
                            # as we're organizing deaths by the person's super_area, not the hospital's region
                            if hospital_id in world.hospitals.id_to_hospital:
                                daily_deaths_in_hospital[(region, sex, age_group)] += 1
                                daily_deaths_in_hospital_by_area[super_area, sex, age_group] += 1
                            else:
                                logger.warning(f"Hospital ID {hospital_id} referenced in death record not found")
                        except (IndexError, KeyError, AttributeError) as e:
                            logger.warning(f"Error processing hospital death for person {person_id}: {str(e)}")
                            continue
                except AttributeError as e:
                    # This can happen if person object exists but has incomplete data
                    # (e.g., no super_area, area, etc.)
                    logger.warning(f"Person ID {person_id} has incomplete data: {str(e)}")
                    missing_ids.append(f"{person_id} (incomplete data)")
                    continue
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Error processing death for person ID {person_id}: {str(e)}")
                missing_ids.append(f"{person_id} (processing error)")
                continue

        # Log summary of missing IDs if any were found
        if missing_ids:
            logger.warning(f"Found {len(missing_ids)} problem person IDs in death records")
            if len(missing_ids) <= 20:  # Only log if there aren't too many
                logger.warning(f"Problem IDs: {', '.join(missing_ids)}")

        return (
            daily_deaths,
            daily_deaths_in_hospital,
            daily_deaths_by_area,
            daily_deaths_in_hospital_by_area
        )
    
    """ def summarise_deaths(self, world="World"):
        daily_deaths, daily_deaths_in_hospital = defaultdict(int), defaultdict(int)
        for i, person_id in enumerate(self.events["deaths"].dead_person_ids):
            region = world.people.get_from_id(person_id).super_area.region.name
            daily_deaths[region] += 1
            if self.events["deaths"].location_specs[i] == "hospital":
                hospital_id = self.events["deaths"].location_ids[i]
                region = world.hospitals.get_from_id(hospital_id).region_name
                daily_deaths_in_hospital[region] += 1
        return daily_deaths, daily_deaths_in_hospital """

    def get_age_bin(self, age):
        """Convert an age to a 5-year bin string."""
        if age is None:
            return "Unknown"
        lower_bound = (age // 5) * 5
        upper_bound = lower_bound + 4
        return f"{lower_bound}-{upper_bound}"

    def get_person_details(self, person_id, world):
        """Get demographic details for a person."""
        person = world.people.get_from_id(person_id)
        if not person:
            return {"age": None, "gender": "Unknown", "area": "Unknown", "age_bin": "Unknown"}
        
        age = person.age
        return {
            "age": age,
            "gender": person.sex,
            "area": person.area.name if person.area else "Unknown",
            "age_bin": self.get_age_bin(age)
        }
    
    def summarise_infections_by_area(self, world):
        """Summarize infections by area."""
        daily_infections = defaultdict(int)
        for infected_id in self.events["infections"].infected_ids:
            details = self.get_person_details(infected_id, world)
            daily_infections[details["area"]] += 1
        return daily_infections

    def summarise_infections_by_gender(self, world):
        """Summarize infections by gender."""
        daily_infections = defaultdict(int)
        for infected_id in self.events["infections"].infected_ids:
            details = self.get_person_details(infected_id, world)
            daily_infections[details["gender"]] += 1
        return daily_infections

    def summarise_infections_by_age_bin(self, world):
        """Summarize infections by age bin."""
        daily_infections = defaultdict(int)
        for infected_id in self.events["infections"].infected_ids:
            details = self.get_person_details(infected_id, world)
            daily_infections[details["age_bin"]] += 1
        return daily_infections
    
    def summarise_infections_by_area_gender_age(self, world):
        """Summarize infections by area, gender, and age bin combined."""
        daily_infections = defaultdict(int)
        for infected_id in self.events["infections"].infected_ids:
            details = self.get_person_details(infected_id, world)
            key = (details["area"], details["gender"], details["age_bin"])
            daily_infections[key] += 1
        return daily_infections

    def summarise_time_step(self, timestamp: str, world: "World"):
        """
        Summarises infections, hospitalisations, and deaths at both regional and area levels,
        and writes the data to CSV files.

        Args:
            timestamp (str): The current simulation time step.
            world ("World"): The simulation world object.

        Returns:
            None
        """

        # Retrieve infection, hospitalisation, and death summaries
        daily_infected, current_infected, daily_infected_by_area, current_infected_by_area = self.summarise_infections(world=world)

        (
            daily_hospitalised,
            daily_intensive_care,
            current_hospitalised,
            current_intensive_care,
            current_hospitalised_by_area,
            current_intensive_care_by_area,
            hospital_admissions_by_area,
            icu_admissions_by_area
        ) = self.summarise_hospitalisations(world=world)

        (
            daily_deaths,
            daily_deaths_in_hospital,
            daily_deaths_by_area,
            daily_deaths_in_hospital_by_area
        ) = self.summarise_deaths(world=world)

        # Collect all unique regions
        all_hospital_regions = {hospital.region_name for hospital in world.hospitals}
        all_world_regions = {region.name for region in world.regions}
        all_regions = all_hospital_regions | all_world_regions  # Union of sets

        # Collect all unique region-based keys
        all_region_keys = set(
            daily_infected.keys()
        ).union(
            current_infected.keys(),
            daily_hospitalised.keys(),
            daily_intensive_care.keys(),
            current_hospitalised.keys(),
            current_intensive_care.keys(),
            daily_deaths.keys(),
            daily_deaths_in_hospital.keys()
        )

        # Write region-level summary
        region_summary_path = self.record_path / self.summary_filename
        with open(region_summary_path, "a", newline="") as summary_file:
            summary_writer = csv.writer(summary_file)

            # Write header if the file is empty
            if region_summary_path.stat().st_size == 0:
                summary_writer.writerow([
                    "time_stamp", "region", "sex", "age_group",
                    "current_infected", "daily_infected",
                    "current_hospitalised", "daily_hospitalised",
                    "current_intensive_care", "daily_intensive_care",
                    "daily_deaths_in_hospital", "daily_deaths"
                ])

            for (region, sex, age_group) in all_region_keys:
                data = [
                    current_infected.get((region, sex, age_group), 0),
                    daily_infected.get((region, sex, age_group), 0),
                    current_hospitalised.get((region, sex, age_group), 0),
                    daily_hospitalised.get((region, sex, age_group), 0),
                    current_intensive_care.get((region, sex, age_group), 0),
                    daily_intensive_care.get((region, sex, age_group), 0),
                    daily_deaths_in_hospital.get((region, sex, age_group), 0),
                    daily_deaths.get((region, sex, age_group), 0),
                ]
                if sum(data) > 0:
                    summary_writer.writerow(
                        [timestamp.strftime("%Y-%m-%d"), region, sex, age_group] + data
                    )

        # Collect all unique area-based keys
        all_areas = set()

        # Ensure only valid (area, sex, age_group) tuples are included
        for data_dict in [
            current_infected_by_area, daily_infected_by_area, current_hospitalised_by_area,
            hospital_admissions_by_area, current_intensive_care_by_area, icu_admissions_by_area,
            daily_deaths_in_hospital_by_area, daily_deaths_by_area
        ]:
            for key in data_dict.keys():
                if isinstance(key, tuple) and len(key) == 3:
                    all_areas.add(key)  # Add only properly formatted keys

        # Write area-level summary
        area_summary_path = self.record_path / "summary_area.csv"
        with open(area_summary_path, "a", newline="") as area_file:
            area_writer = csv.writer(area_file)

            # Write header if the file is empty
            if area_summary_path.stat().st_size == 0:
                area_writer.writerow([
                    "time_stamp", "super_area", "sex", "age_group",
                    "current_infected", "daily_infected",
                    "current_hospitalised", "daily_hospitalised",
                    "current_intensive_care", "daily_intensive_care",
                    "daily_deaths_in_hospital", "daily_deaths"
                ])

            for (area, sex, age_group) in all_areas:
                data = [
                    current_infected_by_area.get((area, sex, age_group), 0),
                    daily_infected_by_area.get((area, sex, age_group), 0),
                    current_hospitalised_by_area.get((area, sex, age_group), 0),
                    hospital_admissions_by_area.get((area, sex, age_group), 0),
                    current_intensive_care_by_area.get((area, sex, age_group), 0),
                    icu_admissions_by_area.get((area, sex, age_group), 0),
                    daily_deaths_in_hospital_by_area.get((area, sex, age_group), 0),
                    daily_deaths_by_area.get((area, sex, age_group), 0)
                ]

                # Write only if there are nonzero values
                if sum(data) > 0:
                    area_writer.writerow([timestamp.strftime("%Y-%m-%d"), area, sex, age_group] + data)

                    
    """ def summarise_time_step(self, timestamp: str, world: "World"):
        daily_infected, current_infected = self.summarise_infections(world=world)
        (
            daily_hospitalised,
            daily_intensive_care,
            current_hospitalised,
            current_intensive_care,
        ) = self.summarise_hospitalisations(world=world)

        daily_deaths, daily_deaths_in_hospital = self.summarise_deaths(world=world)
        all_hospital_regions = [hospital.region_name for hospital in world.hospitals]
        all_world_regions = [region.name for region in world.regions]
        all_regions = set(all_hospital_regions + all_world_regions)
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
                    ) """


    def combine_outputs(self, remove_left_overs=True):
        combine_records(self.record_path, remove_left_overs=remove_left_overs)

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
        if activity_manager is not None:
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
        if epidemiology:
            infection_seeds = epidemiology.infection_seeds
            infection_selectors = epidemiology.infection_selectors
        if self.mpi_rank is None or self.mpi_rank == 0:
            self.parameters_interaction(interaction=interaction)
            self.parameters_seed(infection_seeds=infection_seeds)
            self.parameters_infection(infection_selectors=infection_selectors)
            self.parameters_policies(activity_manager=activity_manager)

    def meta_information(
        self,
        comment: Optional[str] = None,
        random_state: Optional[int] = None,
        number_of_cores: Optional[int] = None,
    ):
        if self.mpi_rank is None or self.mpi_rank == 0:
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


import pandas as pd
from pathlib import Path

import pandas as pd
import numpy as np
from pathlib import Path

def combine_summaries(record_path, remove_left_overs=False, save_dir=None):
    record_path = Path(record_path)
    summary_files = list(record_path.glob("summary.*.csv"))

    print("\nDEBUG: Found summary files ->", summary_files)

    if not summary_files:
        print("\nERROR: No summary files found in", record_path)
        return

    dfs = []
    for summary_file in summary_files:
        print("\nDEBUG: Processing file ->", summary_file)
        
        try:
            df = pd.read_csv(summary_file)
            print("\nDEBUG: File shape ->", df.shape)

            if df.empty:
                print("\nWARNING: File is empty, skipping ->", summary_file)
                continue

            # Aggregation logic
            aggregator = {col: "mean" if "current" in col else "sum" for col in df.columns[2:]}
            print("\nDEBUG: Aggregation dictionary ->", aggregator)

            # Group and aggregate
            df = df.groupby(["region", "time_stamp"], as_index=False).agg(aggregator)
            print("\nDEBUG: DataFrame after aggregation ->\n", df.head())

            dfs.append(df)

            if remove_left_overs:
                summary_file.unlink()
                print("\nDEBUG: Removed file ->", summary_file)

        except Exception as e:
            print("\nERROR: Failed to read file ->", summary_file)
            print("Exception:", e)

    if not dfs:
        print("\nERROR: No valid dataframes found, cannot concatenate")
        return

    print("\nDEBUG: Concatenating", len(dfs), "dataframes.")
    summary = pd.concat(dfs)
    print("\nDEBUG: Summary shape after concatenation ->", summary.shape)

    # Group and finalize the summary
    summary = summary.groupby(["region", "time_stamp"], as_index=False).sum()
    print("\nDEBUG: Final summary after grouping ->\n", summary.head())

    # Save the combined region summary
    save_path = Path(save_dir) if save_dir else record_path
    full_summary_save_path = save_path / "summary.csv"
    summary.to_csv(full_summary_save_path, index=False)
    print("\nDEBUG: Successfully saved region summary to", full_summary_save_path)

    # Combine area-level summaries
    area_summary_file = record_path / "summary_area.csv"
    if area_summary_file.exists():
        try:
            area_df = pd.read_csv(area_summary_file)
            print("\nDEBUG: Area file shape ->", area_df.shape)

            area_aggregator = {
                "current_infected": lambda x: np.ceil(np.mean(x)),
                "daily_infected": "sum",
                "current_hospitalised": lambda x: np.ceil(np.mean(x)),
                "daily_hospitalised": "sum",
                "current_intensive_care": lambda x: np.ceil(np.mean(x)),
                "daily_intensive_care": "sum",
                "daily_deaths": "sum",
                "daily_deaths_in_hospital": "sum"
            }

            area_summary = area_df.groupby(["time_stamp", "area"], as_index=False).agg(area_aggregator)
            print("\nDEBUG: Area summary after aggregation ->\n", area_summary.head())

            full_area_summary_save_path = save_path / "summary_area_final.csv"
            area_summary.to_csv(full_area_summary_save_path, index=False)
            print("\nDEBUG: Successfully saved area summary to", full_area_summary_save_path)

            if remove_left_overs:
                area_summary_file.unlink()
                print("\nDEBUG: Removed area summary file ->", area_summary_file)

        except Exception as e:
            print("\nERROR: Failed to process area summary ->", area_summary_file)
            print("Exception:", e)

    print("\nDEBUG: Summary combination completed!")


def combine_hdf5s(
    record_path,
    table_names=("infections", "population"),
    remove_left_overs=False,
    save_dir=None,
):
    record_files = record_path.glob("june_record.*.h5")
    if save_dir is None:
        save_path = Path(record_path)
    else:
        save_path = Path(save_dir)
    full_record_save_path = save_path / "june_record.h5"
    with tables.open_file(full_record_save_path, "w") as merged_record:
        for i, record_file in enumerate(record_files):
            with tables.open_file(str(record_file), "r") as record:
                datasets = record.root._f_list_nodes()
                for dataset in datasets:
                    arr_data = dataset[:]
                    if i == 0:
                        description = getattr(record.root, dataset.name).description
                        merged_record.create_table(
                            merged_record.root, dataset.name, description=description
                        )
                    if len(arr_data) > 0:
                        table = getattr(merged_record.root, dataset.name)
                        table.append(arr_data)
                        table.flush()
            if remove_left_overs:
                record_file.unlink()


def combine_records(record_path, remove_left_overs=False, save_dir=None):
    record_path = Path(record_path)
    combine_summaries(
        record_path, remove_left_overs=remove_left_overs, save_dir=save_dir
    )
    combine_hdf5s(record_path, remove_left_overs=remove_left_overs, save_dir=save_dir)


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

def get_age_group(age: int) -> str:
    """
    Returns a 10-year age bucket as a string.
    Example: 23 -> "20-29", 67 -> "60-69"
    """
    lower_bound = (age // 10) * 10
    upper_bound = lower_bound + 9
    # Make sure you handle 80+ or 90+ as needed:
    if lower_bound >= 80:
        return "80+"
    return f"{lower_bound}-{upper_bound}"
