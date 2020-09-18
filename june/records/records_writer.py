from tables import *
import os
import pandas as pd
import numpy as np
from pathlib import Path

from typing import Optional, List
from june.records.helpers_recors_writer import InfectionRecord, HospitalAdmissionsRecord


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
        self.file = open_file(self.record_path / filename, mode="w")
        self.root = self.file.root
        self.locations_to_store = locations_to_store
        self.initialize_tables()

    def initialize_tables(self):
        self.infections_group = self.file.create_group(self.root, "infections")
        self.infection_table = self.file.create_table(
            self.infections_group, "readout", InfectionRecord
        )
        self.hosp_admission_group = self.file.create_group(
            self.root, "hospital_admissions"
        )
        self.hosp_admission_table = self.file.create_table(
            self.hosp_admission_group, "readout", HospitalAdmissionsRecord
        )
        self.icu_admission_group = self.file.create_group(self.root, "icu_admissions")
        self.icu_admission_table = self.file.create_table(
            self.icu_admission_group, "readout", HospitalAdmissionsRecord
        )

    def get_global_location_id(self, location: str) -> int:
        location_id = int(location.split("_")[-1])
        location_type = "_".join(location.split("_")[:-1])
        order_in_keys = list(self.locations_to_store.keys()).index(location_type)
        n_previous_locations = sum(list(self.locations_to_store.values())[:order_in_keys])
        global_location_id = n_previous_locations + location_id 
        return global_location_id

    def locations(self,):
        pass

    def infections(
        self, time_stamp: str, location: str, new_infected_ids: List[int]
    ):
        location_id = self.get_global_location_id(location)
        data = np.rec.fromarrays(
            (
                np.array(
                    [time_stamp.strftime("%Y-%m-%d")] * len(new_infected_ids),
                    dtype="S10",
                ),
                np.array([location_id] * len(new_infected_ids), dtype=np.int32),
                np.array(new_infected_ids, dtype=np.int32),
            )
        )
        self.infection_table.append(data)
        self.infection_table.flush()

    def hospital_admission(self, time_stamp: str, hospital_id: int, patient_id: int):
        data = np.rec.fromarrays(
            (
                np.array([time_stamp.strftime("%Y-%m-%d")], dtype="S10"),
                np.array([hospital_id], dtype=np.int32),
                np.array([patient_id], dtype=np.int32),
            )
        )
        self.hosp_admission_table.append(data)
        self.hosp_admission_table.flush()

    def intensive_care_admission(
        self, time_stamp: str, hospital_id: int, patient_id: int
    ):
        data = np.rec.fromarrays(
            (
                np.array([time_stamp.strftime("%Y-%m-%d")], dtype="S10"),
                np.array([hospital_id], dtype=np.int32),
                np.array([patient_id], dtype=np.int32),
            )
        )
        self.icu_admission_table.append(data)
        self.icu_admission_table.flush()

    def death(self, time_stamp: str, location_id: int, patient_id: int):
        # location, one of: household, hospital, icu_ward
        # Use location id to infer whether a person died in hospital, how do we differentiate between ICU  ward or non ICU? -> through icu admissions

        pass
