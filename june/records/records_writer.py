import os
import tables
import pandas as pd
import numpy as np
import csv
from pathlib import Path
from typing import Optional, List
from collections import Counter, defaultdict

from june.groups import Supergroup
from june.records.event_records_writer import (
    InfectionRecord,
    HospitalAdmissionsRecord,
    ICUAdmissionsRecord,
    DischargesRecord,
    DeathsRecord,
    RecoveriesRecord,
    SymptomsRecord,
)
from june.records.static_records_writer import (
    PeopleRecord,
    LocationRecord,
    AreaRecord,
    SuperAreaRecord,
    RegionRecord,
)
from june import paths


def combine_summaries(record_path):
    summary_files = record_path.glob("summary.*.csv")
    dfs = []
    for summary_file in summary_files:
        dfs.append(pd.read_csv(summary_file))
    summary = pd.concat(dfs)
    summary = summary.groupby(["time_stamp", "region"]).sum()
    summary.to_csv(record_path / "summary.csv")


def combine_hdf5s(record_path, table_names=("infections", "population")):
    record_files = record_path.glob("june_record.*.h5")
    with tables.open_file(record_path / "june_record.h5", "w") as merged_record:
        for i, record_file in enumerate(record_files):
            with tables.open_file(str(record_file), "r") as record:
                datasets = record.root._f_list_nodes()
                for dataset in datasets:
                    arr_data = dataset[:]
                    if len(arr_data) > 0:
                        if i == 0:
                            description = getattr(record.root, dataset.name).description
                            merged_record.create_table(
                                merged_record.root,
                                dataset.name,
                                description=description,
                            )
                        table = getattr(merged_record.root, dataset.name)
                        table.append(arr_data)
                        table.flush()


def combine_records(record_path):
    record_path = Path(record_path)
    combine_summaries(record_path)
    combine_hdf5s(record_path)


class Record:
    def __init__(
        self, record_path: str, record_static_data=False, mpi_rank: Optional[int] = None
    ):
        self.record_path = Path(record_path)
        self.record_path.mkdir(parents=True, exist_ok=True)
        if mpi_rank is not None:
            self.filename = f"june_record.{mpi_rank}.h5"
            self.summary_filename = f"summary.{mpi_rank}.csv"
        else:
            self.filename = f"june_record.h5"
            self.summary_filename = f"summary.csv"
        try:
            os.remove(self.record_path / self.filename)
        except OSError:
            pass
        self.file = tables.open_file(self.record_path / self.filename, mode="w")
        self.root = self.file.root
        self.events = {
            "infections": InfectionRecord(hdf5_file=self.file),
            "hospital_admissions": HospitalAdmissionsRecord(hdf5_file=self.file),
            "icu_admissions": ICUAdmissionsRecord(hdf5_file=self.file),
            "discharges": DischargesRecord(hdf5_file=self.file),
            "deaths": DeathsRecord(hdf5_file=self.file),
            "recoveries": RecoveriesRecord(hdf5_file=self.file),
            "symptoms": SymptomsRecord(hdf5_file=self.file),
        }
        with open(
            self.record_path / self.summary_filename, "w", newline=""
        ) as summary_file:
            writer = csv.writer(summary_file)
            fields = ["infected", "recovered", "hospitalised", "intensive_care"]
            header = ["time_stamp", "region"]
            for field in fields:
                header.append("current_" + field)
                header.append("daily_" + field)
            header.extend(
                ["current_susceptible", "daily_hospital_deaths", "daily_deaths"]
            )
            writer.writerow(header)
        if record_static_data:
            self.statics = {
                "people": PeopleRecord(hdf5_file=self.file),
                "locations": LocationRecord(hdf5_file=self.file),
                "areas": AreaRecord(hdf5_file=self.file),
                "super_areas": SuperAreaRecord(hdf5_file=self.file),
                "regions": RegionRecord(hdf5_file=self.file),
            }
        self.file.close()

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

    def summarise_hospitalisations(self, world: "World"):
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
        for person in world.people:
            if person.medical_facility is not None:
                if person.medical_facility.subgroup_type == 1:
                    region = person.medical_facility.group.region_name
                    current_hospitalised[region] += 1
                elif person.medical_facility.subgroup_type == 2:
                    region = person.medical_facility.group.region_name
                    current_intensive_care[region] += 1
        return (
            hospital_admissions,
            icu_admissions,
            current_hospitalised,
            current_intensive_care,
        )

    def summarise_infections(self, world="World"):
        daily_infections, current_infected = defaultdict(int), defaultdict(int)
        for region in self.events["infections"].region_names:
            daily_infections[region] += 1
        for person in world.people.infected:
            region = person.super_area.region.name
            current_infected[region] += 1
        return daily_infections, current_infected

    def summarise_recoveries(self, world="World"):
        daily_recovered, current_recovered = defaultdict(int), defaultdict(int)
        for person_id in self.events["recoveries"].recovered_person_ids:
            region = world.people.get_from_id(person_id).super_area.region.name
            daily_recovered[region] += 1
        for person in world.people:
            if person.recovered:
                region = person.super_area.region.name
                current_recovered[region] += 1
        return daily_recovered, current_recovered

    def summarise_deaths(self, world="World"):
        daily_deaths, daily_deaths_in_hospital = defaultdict(int), defaultdict(int)
        for i, person_id in enumerate(self.events["deaths"].dead_person_ids):
            region = world.people.get_from_id(person_id).super_area.region.name
            daily_deaths[region] += 1
            if self.events["deaths"].location_specs[i] == "hospital":
                hospital_id = self.events["deaths"].location_ids[i]
                region = world.hospitals.get_from_id(hospital_id).region_name
                daily_deaths_in_hospital[region] += 1
        return daily_deaths, daily_deaths_in_hospital

    def summarise_susceptibles(self, world="World"):
        current_susceptible = {}
        for region in world.regions:
            current_susceptible[region.name] = len(
                [person for person in region.people if person.susceptible]
            )
        return current_susceptible

    def summarise_time_step(self, timestamp: str, world: "World"):
        daily_infected, current_infected = self.summarise_infections(world=world)
        daily_recovered, current_recovered = self.summarise_recoveries(world=world)
        (
            daily_hospitalised,
            daily_intensive_care,
            current_hospitalised,
            current_intensive_care,
        ) = self.summarise_hospitalisations(world=world)
        current_susceptible = self.summarise_susceptibles(world=world)
        daily_deaths, daily_deaths_in_hospital = self.summarise_deaths(world=world)
        with open(
            self.record_path / self.summary_filename, "a", newline=""
        ) as summary_file:
            summary_writer = csv.writer(summary_file)
            for region in [region.name for region in world.regions]:
                summary_writer.writerow(
                    [
                        timestamp.strftime("%Y-%m-%d"),
                        region,
                        current_infected.get(region, 0),
                        daily_infected.get(region, 0),
                        current_recovered.get(region, 0),
                        daily_recovered.get(region, 0),
                        current_hospitalised.get(region, 0),
                        daily_hospitalised.get(region, 0),
                        current_intensive_care.get(region, 0),
                        daily_intensive_care.get(region, 0),
                        current_susceptible.get(region, 0),
                        daily_deaths_in_hospital.get(region, 0),
                        daily_deaths.get(region, 0),
                    ]
                )

    def combine_outputs(self,):
        combine_records(self.record_path)
