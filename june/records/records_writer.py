from tables import *
import os
import pandas as pd
import numpy as np
import csv
from pathlib import Path
from typing import Optional, List
from collections import Counter

from june.records.helpers_recors_writer import (
    InfectionRecord,
    HospitalAdmissionsRecord,
    DeathsRecord,
    RecoveriesRecord,
)
from june import paths

# TODO: record hospital occupancy, static datasets

class Record:
    def __init__(
        self,
        record_path: str,
        filename: str,
        locations_to_store: dict = {
            "household": 1,
            "care_home": 1,
            "school": 1,
            "company": 1,
            "pub": 1,
            "cinema": 1,
            "grocery": 1,
            "commute_unit": 1,
            "commute_city_unit": 1,
        },
    ):
        self.record_path = Path(record_path)
        self.record_path.mkdir(parents=True, exist_ok=True)
        try:
            os.remove(self.record_path / filename)
        except OSError:
            pass
        self.filename = filename
        self.file = open_file(self.record_path / self.filename, mode="w")
        self.root = self.file.root
        self.locations_to_store = locations_to_store
        self.initialize_tables()
        self.file.close()
        with open(self.record_path / "summary.csv", mode="w") as summary_file:
            summary_file.write(
                "time_stamp,region,daily_infections_by_residence," +
                "daily_hospital_admissions,daily_icu_admissions," +
                "daily_deaths_by_residence,daily_care_home_deaths,daily_hospital_deaths\n"
            )

    def initialize_tables(self):
        self.infection_locations, self.new_infected_ids = [], []
        self.infections_table = self.file.create_table(
            self.root, "infections", InfectionRecord
        )
        self.hospital_ids, self.patient_ids = [], []
        self.hosp_admission_table = self.file.create_table(
            self.root, "hospital_admissions", HospitalAdmissionsRecord
        )
        self.icu_hospital_ids, self.icu_patient_ids = [], []
        self.icu_admission_table = self.file.create_table(
            self.root, "icu_admissions", HospitalAdmissionsRecord
        )
        self.death_location_ids, self.dead_person_ids = [], []
        self.deaths_table = self.file.create_table(self.root, "deaths", DeathsRecord)
        self.recovered_person_id = []
        self.recoveries_table = self.file.create_table(self.root, "recoveries", RecoveriesRecord)

    def get_global_location_id(self, location: str) -> int:
        location_id = int(location.split("_")[-1])
        location_type = "_".join(location.split("_")[:-1])
        order_in_keys = list(self.locations_to_store.keys()).index(location_type)
        n_previous_locations = sum(
            list(self.locations_to_store.values())[:order_in_keys]
        )
        global_location_id = n_previous_locations + location_id
        return global_location_id

    def invert_global_location_id(self, location_global_id: int) -> (str, int):
        cummulative_values = np.cumsum(list(self.locations_to_store.values()))
        idx = np.digitize(location_global_id, cummulative_values)
        location_type = list(self.locations_to_store.keys())[idx]
        if idx == 0:
            location_id = location_global_id
        else:
            location_id = location_global_id - cummulative_values[idx - 1]
        return location_type, location_id

    def locations(self,):
        pass

    def accumulate_infections(self, location, new_infected_ids):
        location_id = self.get_global_location_id(location)
        self.infection_locations.extend([location_id] * len(new_infected_ids))
        self.new_infected_ids.extend(new_infected_ids)

    def accumulate_hospitalisation(self, hospital_id, patient_id, intensive_care=False):
        if intensive_care:
            self.icu_hospital_ids.append(hospital_id)
            self.icu_patient_ids.append(patient_id)
        else:
            self.hospital_ids.append(hospital_id)
            self.patient_ids.append(patient_id)

    def accumulate_death(self, death_location, dead_person_id):
        death_location_id = self.get_global_location_id(death_location)
        self.death_location_ids.append(death_location_id)
        self.dead_person_ids.append(dead_person_id)

    def infections(
        self, time_stamp: str,
    ):
        data = np.rec.fromarrays(
            (
                np.array(
                    [time_stamp.strftime("%Y-%m-%d")] * len(self.new_infected_ids),
                    dtype="S10",
                ),
                np.array(self.infection_locations, dtype=np.int32),
                np.array(self.new_infected_ids, dtype=np.int32),
            )
        )
        self.file.root.infections.append(data)
        self.file.root.infections.flush()
        self.infection_locations, self.new_infected_ids = [], []

    def hospital_admissions(
        self, time_stamp: str,
    ):
        data = np.rec.fromarrays(
            (
                np.array(
                    [time_stamp.strftime("%Y-%m-%d")] * len(self.patient_ids),
                    dtype="S10",
                ),
                np.array(self.hospital_ids, dtype=np.int32),
                np.array(self.patient_ids, dtype=np.int32),
            )
        )
        self.file.root.hospital_admissions.append(data)
        self.file.root.hospital_admissions.flush()
        self.hospital_ids, self.patient_ids = [], []

    def intensive_care_admissions(
        self, time_stamp: str,
    ):
        data = np.rec.fromarrays(
            (
                np.array(
                    [time_stamp.strftime("%Y-%m-%d")] * len(self.icu_patient_ids),
                    dtype="S10",
                ),
                np.array(self.icu_hospital_ids, dtype=np.int32),
                np.array(self.icu_patient_ids, dtype=np.int32),
            )
        )
        self.file.root.icu_admissions.append(data)
        self.file.root.icu_admissions.flush()
        self.icu_hospital_ids, self.icu_patient_ids = [], []

    def deaths(
        self, time_stamp: str,
    ):
        data = np.rec.fromarrays(
            (
                np.array(
                    [time_stamp.strftime("%Y-%m-%d")] * len(self.dead_person_ids),
                    dtype="S10",
                ),
                np.array(self.death_location_ids, dtype=np.int32),
                np.array(self.dead_person_ids, dtype=np.int32),
            )
        )
        self.file.root.deaths.append(data)
        self.file.root.deaths.flush()
        self.death_location_ids, self.dead_person_ids = [], []

    def recoveries(
        self, time_stamp: str,
    ):
        data = np.rec.fromarrays(
            (
                np.array(
                    [time_stamp.strftime("%Y-%m-%d")] * len(self.dead_person_ids),
                    dtype="S10",
                ),
                np.array(self.recovered_person_id, dtype=np.int32),
            )
        )
        self.file.root.recoveries.append(data)
        self.file.root.recoveries.flush()
        self.recovered_person_id = []



    def summarise_time_step(self, time_stamp: str, world: "World"):
        hospital_regions = [
            world.hospitals[hospital_id].super_area.region.name
            for hospital_id in self.hospital_ids
        ]
        hospitalised_per_region = Counter(hospital_regions)
        intensive_care_regions = [
            world.hospitals[hospital_id].super_area.region.name
            for hospital_id in self.icu_hospital_ids
        ]
        intensive_care_per_region = Counter(intensive_care_regions)
        daily_infected_regions = [
            world.people[person_id].area.super_area.region.name
            for person_id in self.new_infected_ids
        ]
        daily_infected_per_region = Counter(daily_infected_regions)

        deaths_regions = [
            world.people[person_id].area.super_area.region.name
            for person_id in self.dead_person_ids
        ]
        all_deaths_per_region = Counter(deaths_regions)

        hospital_deaths_regions, care_home_deaths_regions = [], []
        for death_location_id in self.death_location_ids:
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
        with open(self.record_path / "summary.csv", "a", newline="") as summary_file:
            summary_writer = csv.writer(summary_file)
            for region in [region.name for region in world.regions]:
                summary_writer.writerow(
                    [
                        time_stamp,
                        region,
                        daily_infected_per_region.get(region, 0),
                        hospitalised_per_region.get(region, 0),
                        intensive_care_per_region.get(region, 0),
                        all_deaths_per_region.get(region, 0),
                        care_home_deaths_per_region.get(region, 0),
                        hospital_deaths_per_region.get(region, 0),
                    ]
                )

    def time_step(self, time_stamp: str):
        self.file = open_file(self.record_path / self.filename, mode="a")
        self.infections(time_stamp=time_stamp)
        self.hospital_admissions(time_stamp=time_stamp)
        self.intensive_care_admissions(time_stamp=time_stamp)
        self.deaths(time_stamp=time_stamp)
        self.recoveries(time_stamp=time_stamp)
        self.file.close()
