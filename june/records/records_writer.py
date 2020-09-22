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
)
from june import paths

default_super_area_region_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)


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
        super_area_region_filename: Optional[str] = default_super_area_region_filename,
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
        if super_area_region_filename is not None:
            # write header summary
            with open(self.record_path / "summary.csv", mode="w") as summary_file:
                summary_file.write(
                    "time_stamp,region,daily_infections,daily_hospital_admissions,daily_icu_admissions, \n"
                )

            self.super_area_region_df = pd.read_csv(super_area_region_filename)[
                ["super_area", "region"]
            ].drop_duplicates()
            self.super_area_region_df.set_index("super_area", inplace=True)

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
        print(cummulative_values)
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

    def summarise_time_step(self, time_stamp: str, hospitals: "World"):
        hospital_super_areas = [
            hospitals[hospital_id].super_area for hospital_id in self.hospital_ids
        ]
        hospital_regions = Counter(
            self.super_area_region_df.loc[hospital_super_areas].region
        )
        intensive_care_super_areas = [
            hospitals[hospital_id].super_area for hospital_id in self.icu_hospital_ids
        ]
        intensive_care_regions = Counter(
            self.super_area_region_df.loc[intensive_care_super_areas].region
        )
        with open(self.record_path / "summary.csv", "a", newline="") as summary_file:
            summary_writer = csv.writer(summary_file)
            for region in self.super_area_region_df.region.unique():
                summary_writer.writerow(
                    [
                        time_stamp,
                        region,
                        hospital_regions.get(region, 0),
                        intensive_care_regions.get(region, 0),
                    ]
                )
        """
        location_regions = (self.infection_locations)
        icu_admissions_regions = (self.icu_hospital_ids)
        deaths_region
        hospital_deaths_region
        """
        # make sure all Counters give same order in regions
        # add row to csv ('daily_hospital_admissions', 'daily_icu_admissions', 'daily_home_deaths', 'daily_hospital_deaths' 'daily_care_home_deaths' 'region')

    def record_time_step(self, time_stamp: str):
        self.file = open_file(self.record_path / self.filename, mode="a")
        self.infections(time_stamp=time_stamp)
        self.hospital_admissions(time_stamp=time_stamp)
        self.intensive_care_admissions(time_stamp=time_stamp)
        self.deaths(time_stamp=time_stamp)
        self.file.close()
