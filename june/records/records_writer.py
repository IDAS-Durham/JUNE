import os
import tables
import pandas as pd
import numpy as np
import csv
from pathlib import Path
from typing import Optional, List
from collections import Counter

from june.groups import Supergroup
from june.records.helpers_recors_writer import (
    InfectionRecord,
    HospitalAdmissionsRecord,
    ICUAdmissionsRecord,
    DeathsRecord,
    RecoveriesRecord,
)
from june import paths


class Record:
    def __init__(
        self,
        record_path: str,
        filename: str,
        locations_counts: dict = {"household": 1, "care_home": 1,},
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
                    "daily_care_home_deaths",
                    "daily_hospital_deaths",
                ]
            )

        self.file.close()

    @classmethod
    def from_world(cls, record_path: str, filename: str, world: "World"):
        all_super_groups = []
        for attribute, value in world.__dict__.items():
            if isinstance(value, Supergroup):
                all_super_groups.append(attribute)
        locations_counts = {}
        for sg in all_super_groups:
            super_group = getattr(world, sg)
            locations_counts[super_group.group_spec] = len(super_group)
        print(locations_counts)
        return cls(
            record_path=record_path,
            filename=filename,
            locations_counts=locations_counts,
        )

    def get_global_location_id(self, location: str) -> int:
        location_id = int(location.split("_")[-1])
        location_type = "_".join(location.split("_")[:-1])
        order_in_keys = list(self.locations_counts.keys()).index(location_type)
        n_previous_locations = sum(list(self.locations_counts.values())[:order_in_keys])
        global_location_id = n_previous_locations + location_id
        return global_location_id

    def invert_global_location_id(self, location_global_id: int) -> (str, int):
        cummulative_values = np.cumsum(list(self.locations_counts.values()))
        idx = np.digitize(location_global_id, cummulative_values)
        location_type = list(self.locations_counts.keys())[idx]
        if idx == 0:
            location_id = location_global_id
        else:
            location_id = location_global_id - cummulative_values[idx - 1]
        return location_type, location_id

    def accumulate_infections(self, location, new_infected_ids):
        location_id = self.get_global_location_id(location)
        self.events["infections"].accumulate(
            infection_location_id=location_id, new_infected_ids=new_infected_ids
        )

    def accumulate_hospitalisation(self, hospital_id, patient_id, intensive_care=False):
        if intensive_care:
            self.events["icu_admissions"].accumulate(
                hospital_id=hospital_id, patient_id=patient_id
            )
        else:
            self.events["hospital_admissions"].accumulate(
                hospital_id=hospital_id, patient_id=patient_id
            )

    def accumulate_death(self, death_location, dead_person_id):
        death_location_id = self.get_global_location_id(death_location)
        self.events["deaths"].accumulate(
            death_location_id=death_location_id, dead_person_id=dead_person_id
        )

    def accumulate_recoveries(self, recovered_person_id):
        self.events["recoveries"].accumulate(recovered_person_id=recovered_person_id,)

    def time_step(self, timestamp: str):
        self.file = tables.open_file(self.record_path / self.filename, mode="a")
        for event_name in self.events.keys():
            self.events[event_name].record(hdf5_file=self.file, timestamp=timestamp)
        self.file.close()

    def summarise_hospitalisations(self, timestamp: str, world: "World"):
        hospitalised_per_region = Counter(
            [
                world.hospitals[hospital_id].super_area.region.name
                for hospital_id in self.events["hospital_admissions"].hospital_ids
            ]
        )
        intensive_care_per_region = Counter(
            [
                world.hospitals[hospital_id].super_area.region.name
                for hospital_id in self.events["icu_admissions"].hospital_ids
            ]
        )
        return hospitalised_per_region, intensive_care_per_region

    def summarise_infections(self, timestamp: str, world="World"):
        return Counter(
            [
                world.people[person_id].area.super_area.region.name
                for person_id in self.events["infections"].new_infected_ids
            ]
        )

    def summarise_deaths(self, timestamp: str, world="World"):
        all_deaths_per_region = Counter(
            [
                world.people[person_id].area.super_area.region.name
                for person_id in self.events["deaths"].dead_person_ids
            ]
        )

        hospital_deaths_regions, care_home_deaths_regions = [], []
        for death_location_id in self.events["deaths"].death_location_ids:
            location_type, location_id = self.invert_global_location_id(
                death_location_id
            )
            if location_type == "care_home":
                care_home_deaths_regions.append(
                    world.care_homes[location_id].super_area.region.name
                )
            elif location_type == "hospital":
                hospital_deaths_regions.append(
                    world.hospitals[location_id].super_area.region.name
                )
        hospital_deaths_per_region = Counter(hospital_deaths_regions)
        care_home_deaths_per_region = Counter(care_home_deaths_regions)
        return (
            all_deaths_per_region,
            hospital_deaths_per_region,
            care_home_deaths_per_region,
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
                        care_home_deaths_per_region.get(region, 0),
                        hospital_deaths_per_region.get(region, 0),
                    ]
                )
