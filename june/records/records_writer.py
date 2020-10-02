import os
import tables
import pandas as pd
import yaml
import numpy as np
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from collections import Counter, defaultdict 
import june
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
            self.filename = f"june_record.h5"
            self.summary_filename = f"summary.csv"
        self.configs_filename = f"config.yaml"
        try:
            os.remove(self.record_path / self.filename)
        except OSError:
            pass
        with tables.open_file(self.record_path / self.filename, mode="w") as self.file:
            self.events = {
                "infections": InfectionRecord(hdf5_file=self.file),
                "hospital_admissions": HospitalAdmissionsRecord(hdf5_file=self.file),
                "icu_admissions": ICUAdmissionsRecord(hdf5_file=self.file),
                "discharges": DischargesRecord(hdf5_file=self.file),
                "deaths": DeathsRecord(hdf5_file=self.file),
                "recoveries": RecoveriesRecord(hdf5_file=self.file),
                "symptoms": SymptomsRecord(hdf5_file=self.file),
            }
            if record_static_data:
                self.statics = {
                    "people": PeopleRecord(hdf5_file=self.file),
                    "locations": LocationRecord(hdf5_file=self.file),
                    "areas": AreaRecord(hdf5_file=self.file),
                    "super_areas": SuperAreaRecord(hdf5_file=self.file),
                    "regions": RegionRecord(hdf5_file=self.file),
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
        description = {
            "description": f"Started runnning at {datetime.now()}. Good luck!"
        }
        with open(self.record_path / self.configs_filename, "w") as f:
            yaml.dump(description, f)

    def static_data(self, world: "World"):
        with tables.open_file(self.record_path / self.filename, mode="a") as self.file:
            for static_name in self.statics.keys():
                self.statics[static_name].record(hdf5_file=self.file, world=world)

    def accumulate(self, table_name: str, **kwargs):
        self.events[table_name].accumulate(**kwargs)

    def time_step(self, timestamp: str):
        with tables.open_file(self.record_path / self.filename, mode="a") as self.file:
            for event_name in self.events.keys():
                self.events[event_name].record(hdf5_file=self.file, timestamp=timestamp)

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
        for hospital in world.hospitals:
            if not hospital.external:
                current_hospitalised[hospital.region_name] += len(hospital.patients)
                current_intensive_care[hospital.region_name] += len(hospital.icu_patients)
        return (
            hospital_admissions,
            icu_admissions,
            current_hospitalised,
            current_intensive_care,
        )

    def summarise_susceptibles(self, world="World"):
        current_susceptible = {}
        for region in world.regions:
            current_susceptible[region.name] = len(
                [person for person in region.people if person.susceptible]
            )
        return current_susceptible

    def summarise_infections(self, world="World"):
        daily_infections, current_infected = defaultdict(int), defaultdict(int)
        for region in self.events["infections"].region_names:
            daily_infections[region] += 1
        for region in world.regions:
            current_infected[region.name] = len(
                [person for person in region.people if person.infected]
            )
        return daily_infections, current_infected

    def summarise_recoveries(self, world="World"):
        daily_recovered, current_recovered = defaultdict(int), defaultdict(int)
        for person_id in self.events["recoveries"].recovered_person_ids:
            region = world.people.get_from_id(person_id).super_area.region.name
            daily_recovered[region] += 1
        for region in world.regions:
            current_recovered[region.name] = len(
                [person for person in region.people if person.recovered]
            )
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
        all_hospital_regions = [hospital.region_name for hospital in world.hospitals]
        all_world_regions = [region.name for region in world.regions]
        all_regions = set(all_hospital_regions + all_world_regions)
        with open(
            self.record_path / self.summary_filename, "a", newline=""
        ) as summary_file:
            summary_writer = csv.writer(summary_file)
            for region in all_regions:
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
        if self.mpi_rank == 0:
            combine_records(self.record_path)

    def append_dict_to_configs(self, config_dict):
        with open(self.record_path / self.configs_filename, "r") as f:
            configs = yaml.safe_load(f)
            configs.update(config_dict)
        with open(self.record_path / self.configs_filename, "w") as f:
            yaml.safe_dump(configs, f,  allow_unicode=True, default_flow_style=False, sort_keys=False)

    def parameters_interaction(
        self, interaction: "Interaction" = None,
    ):
        interaction_dict = {}
        interaction_dict["beta"] = interaction.beta
        interaction_dict["alpha_physical"] = interaction.alpha_physical
        interaction_dict["contact_matrices"] = {}
        for key, values in interaction.contact_matrices.items():
            interaction_dict["contact_matrices"][key] = values.tolist()
        interaction_dict[
            "susceptibilities_by_age"
        ] = interaction.susceptibilities_by_age
        self.append_dict_to_configs(config_dict={"interaction": interaction_dict})

    def parameters_seed(
        self, infection_seed: "InfectionSeed" = None,
    ):
        infection_seed_dict = {}
        infection_seed_dict["seed_strength"] = infection_seed.seed_strength
        infection_seed_dict["min_date"] = infection_seed.min_date.strftime('%Y-%m-%d')
        infection_seed_dict["max_date"] = infection_seed.max_date.strftime('%Y-%m-%d')
        self.append_dict_to_configs(config_dict={"infection_seed": infection_seed_dict})

    def parameters_infection(
        self, infection_selector: "InfectionSelector" = None,
    ):
        infection_dict = {}
        infection_dict[
            "asymptomatic_ratio"
        ] = infection_selector.health_index_generator.asymptomatic_ratio
        infection_dict["transmission_type"] = infection_selector.transmission_type
        self.append_dict_to_configs(config_dict={"infection": infection_dict})

    def parameters_policies(
        self, activity_manager: "ActivityManager" = None,
    ):
        policy_dicts = []
        for policy in activity_manager.policies.policies:
            policy_attributes = policy.__dict__.copy()
            if 'start_time' in policy_attributes:
                policy_attributes["start_time"] = policy_attributes['start_time'].strftime('%Y-%m-%d')
            if 'end_time' in policy_attributes:
                policy_attributes["end_time"] = policy_attributes['end_time'].strftime('%Y-%m-%d')
            policy_dicts.append(policy_attributes)
        with open(self.record_path / 'policies.txt', 'w') as fout:
            fout.write(repr(policy_dicts))

    @staticmethod
    def get_username():
        try:
            username = os.getlogin()
        except:
            username = "no_user"
        return username

    def parameters(
        self,
        interaction: "Interaction" = None,
        infection_seed: "InfectionSeed" = None,
        infection_selector: "InfectionSelector" = None,
        activity_manager: "ActivityManager" = None,
    ):
        if self.mpi_rank is None or self.mpi_rank == 0:
            self.parameters_interaction(interaction=interaction)
            self.parameters_seed(infection_seed=infection_seed)
            self.parameters_infection(infection_selector=infection_selector)
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
            except:
                print("Could not record local git SHA")
                meta_dict["local_SHA"] = "unavailable"
            user = self.get_username()
            meta_dict["user"] = user
            if comment is None:
                comment: "No comment provided."
            meta_dict["user_comment"] = f"{comment}"
            meta_dict["june_path"] = str(june.__path__[0])
            meta_dict["number_of_cores"] = number_of_cores
            meta_dict["random_state"] = random_state
            with open(self.record_path / self.configs_filename, "r") as f:
                configs = yaml.safe_load(f)
                configs.update({"meta_information": meta_dict})
            with open(self.record_path / self.configs_filename, "w") as f:
                yaml.safe_dump(configs, f)


def combine_summaries(record_path):
    summary_files = record_path.glob("summary.*.csv")
    dfs = []
    for summary_file in summary_files:
        dfs.append(pd.read_csv(summary_file))
        summary_file.unlink()
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
                    if i == 0:
                        description = getattr(record.root, dataset.name).description
                        merged_record.create_table(
                            merged_record.root, dataset.name, description=description,
                        )
                    if len(arr_data) > 0:
                        table = getattr(merged_record.root, dataset.name)
                        table.append(arr_data)
                        table.flush()

            record_file.unlink()

def combine_records(record_path):
    record_path = Path(record_path)
    combine_summaries(record_path)
    combine_hdf5s(record_path)



