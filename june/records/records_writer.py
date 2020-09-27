import os
import tables
import pandas as pd
import numpy as np
import csv
from pathlib import Path
from typing import Optional, List
from collections import Counter

from june.groups import Supergroup
from june.records.event_records_writer import (
    InfectionRecord,
    HospitalAdmissionsRecord,
    ICUAdmissionsRecord,
    DeathsRecord,
    RecoveriesRecord,
)
from june.records.static_records_writer import (
    PeopleRecord,
    LocationRecord,
    AreaRecord,
    SuperAreaRecord,
    RegionRecord,
)
from june import paths


class Record:
    def __init__(
        self,
        record_path: str,
        filename: str,
        locations_counts: dict = {"household": 1, "care_home": 1,},
        record_static_data=False,
    ):
        self.record_path = Path(record_path)
        self.record_path.mkdir(parents=True, exist_ok=True)
        try:
            os.remove(self.record_path / filename)
        except OSError:
            pass
        self.filename = filename
        self.file = tables.open_file(self.record_path / self.filename, mode="w")
        self.root = self.file.root
        self.locations_counts = locations_counts
        self.events = {
            "infections": InfectionRecord(hdf5_file=self.file),
            "hospital_admissions": HospitalAdmissionsRecord(hdf5_file=self.file),
            "icu_admissions": ICUAdmissionsRecord(hdf5_file=self.file),
            "deaths": DeathsRecord(hdf5_file=self.file),
            "recoveries": RecoveriesRecord(hdf5_file=self.file),
        }
        with open(self.record_path / "summary.csv", "w", newline="") as summary_file:
            writer = csv.writer(summary_file)
            writer.writerow(
                [
                    "time_stamp",
                    "region",
                    "daily_infections_by_residence",
                    "daily_hospital_admissions",
                    "daily_icu_admissions",
                    "daily_deaths_by_residence",
                    "daily_household_deaths",
                    "daily_care_home_deaths",
                    "daily_hospital_deaths",
                ]
            )
        if record_static_data:
            self.statics = {
                "people": PeopleRecord(hdf5_file=self.file),
                "locations": LocationRecord(hdf5_file=self.file),
                "areas": AreaRecord(hdf5_file=self.file),
                "super_areas": SuperAreaRecord(hdf5_file=self.file),
                "regions": RegionRecord(hdf5_file=self.file),
            }

        self.file.close()

    @classmethod
    def from_world(
        cls, record_path: str, filename: str, world: "World", record_static_data=False
    ):
        all_super_groups = []
        for attribute, value in world.__dict__.items():
            if isinstance(value, Supergroup) and attribute != "cities":
                all_super_groups.append(attribute)
        locations_counts = {}
        for sg in all_super_groups:
            super_group = getattr(world, sg)
            locations_counts[super_group.group_spec] = len(super_group)
        return cls(
            record_path=record_path,
            filename=filename,
            locations_counts=locations_counts,
            record_static_data=record_static_data,
        )

    def static_data(self, world: "World"):
        self.file = tables.open_file(self.record_path / self.filename, mode="a")
        for static_name in self.statics.keys():
            self.statics[static_name].record(hdf5_file=self.file, world=world)
        self.file.close()

    def accumulate(self, table_name: str, **kwargs):
        self.events[table_name].accumulate(**kwargs)
        
    def time_step(self, timestamp: str):
        self.file = tables.open_file(self.record_path / self.filename, mode="a")
        for event_name in self.events.keys():
            self.events[event_name].record(hdf5_file=self.file, timestamp=timestamp)
        self.file.close()

    def summarise_hospitalisations(self, timestamp: str, world: "World"):
        hospitalised_per_region = Counter(
            [
                world.hospitals.get_from_id(hospital_id).super_area.region.name
                for hospital_id in self.events["hospital_admissions"].hospital_ids
            ]
        )
        intensive_care_per_region = Counter(
            [
                world.hospitals.get_from_id(hospital_id).super_area.region.name
                for hospital_id in self.events["icu_admissions"].hospital_ids
            ]
        )
        return hospitalised_per_region, intensive_care_per_region

    def summarise_infections(self, timestamp: str, world="World"):
        return Counter(
            [
                world.people.get_from_id(person_id).area.super_area.region.name
                for person_id in self.events["infections"].infected_ids
            ]
        )

    def summarise_deaths(self, timestamp: str, world="World"):
        all_deaths_per_region = Counter(
            [
                world.people.get_from_id(person_id).area.super_area.region.name
                for person_id in self.events["deaths"].dead_person_ids
            ]
        )

        hospital_deaths_regions, care_home_deaths_regions, household_deaths_regions = (
            [],
            [],
            [],
        )
        for location_id, location_type in zip(
            self.events["deaths"].location_ids, self.events["deaths"].location_specs
        ):
            if location_type == "care_home":
                care_home_deaths_regions.append(
                    world.care_homes.get_from_id(location_id).super_area.region.name
                )
            elif location_type == "household":
                household_deaths_regions.append(
                    world.households.get_from_id(location_id).super_area.region.name
                )
            elif location_type == "hospital":
                hospital_deaths_regions.append(
                    world.hospitals.get_from_id(location_id).super_area.region.name
                )
        hospital_deaths_per_region = Counter(hospital_deaths_regions)
        care_home_deaths_per_region = Counter(care_home_deaths_regions)
        household_deaths_per_region = Counter(household_deaths_regions)
        return (
            all_deaths_per_region,
            hospital_deaths_per_region,
            care_home_deaths_per_region,
            household_deaths_per_region,
        )

    def summarise_time_step(self, timestamp: str, world: "World"):
        (
            hospitalised_per_region,
            intensive_care_per_region,
        ) = self.summarise_hospitalisations(timestamp=timestamp, world=world)
        daily_infected_per_region = self.summarise_infections(
            timestamp=timestamp, world=world
        )
        (
            all_deaths_per_region,
            hospital_deaths_per_region,
            care_home_deaths_per_region,
            household_deaths_per_region,
        ) = self.summarise_deaths(timestamp=timestamp, world=world)
        with open(self.record_path / "summary.csv", "a", newline="") as summary_file:
            summary_writer = csv.writer(summary_file)
            for region in [region.name for region in world.regions]:
                summary_writer.writerow(
                    [
                        timestamp.strftime("%Y-%m-%d"),
                        region,
                        daily_infected_per_region.get(region, 0),
                        hospitalised_per_region.get(region, 0),
                        intensive_care_per_region.get(region, 0),
                        all_deaths_per_region.get(region, 0),
                        household_deaths_per_region.get(region, 0),
                        care_home_deaths_per_region.get(region, 0),
                        hospital_deaths_per_region.get(region, 0),
                    ]
                )
