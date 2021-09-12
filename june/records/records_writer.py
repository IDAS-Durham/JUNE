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
from typing import Optional, List
from collections import Counter, defaultdict
import logging

import subprocess
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
            self.filename = f"june_record.h5"
            self.summary_filename = f"summary.csv"
        self.configs_filename = f"config.yaml"
        self.record_static_data = record_static_data
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
            if self.record_static_data:
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
            #fields = ["infected", "recovered", "hospitalised", "intensive_care"]
            fields = ["infected", "hospitalised", "intensive_care"]
            header = ["time_stamp", "region"]
            for field in fields:
                header.append("current_" + field)
                header.append("daily_" + field)
            header.extend(
                #["current_susceptible", "daily_hospital_deaths", "daily_deaths"]
                ["daily_hospital_deaths", "daily_deaths"]
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
                current_hospitalised[hospital.region_name] += len(hospital.ward)
                current_intensive_care[hospital.region_name] += len(hospital.icu)
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
        for region in world.regions:
            current_infected[region.name] = len(
                [person for person in region.people if person.infected]
            )
        return daily_infections, current_infected

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
                        [
                            timestamp.strftime("%Y-%m-%d"),
                            region,
                        ]
                        + data
                    )

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

    def parameters_interaction(
        self,
        interaction: "Interaction" = None,
    ):
        if interaction is not None:
            interaction_dict = {}
            interaction_dict["betas"] = interaction.betas
            interaction_dict["alpha_physical"] = interaction.alpha_physical
            interaction_dict["contact_matrices"] = {}
            for key, values in interaction.contact_matrices.items():
                interaction_dict["contact_matrices"][key] = values.tolist()
            self.append_dict_to_configs(config_dict={"interaction": interaction_dict})

    def parameters_seed(
        self,
        infection_seeds: "InfectionSeeds" = None,
    ):
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

    def parameters_infection(
        self,
        infection_selectors: "InfectionSelectors" = None,
    ):
        if infection_selectors is not None:
            save_dict = {}
            for selector in infection_selectors._infection_selectors:
                class_name = selector.infection_class.__name__
                save_dict[class_name] = {}
                save_dict[class_name]["transmission_type"] = selector.transmission_type
            self.append_dict_to_configs(config_dict={"infections": save_dict})

    def parameters_policies(
        self,
        activity_manager: "ActivityManager" = None,
    ):
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
        except:
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


def combine_summaries(record_path, remove_left_overs=False, save_dir=None):
    record_path = Path(record_path)
    summary_files = record_path.glob("summary.*.csv")
    dfs = []
    for summary_file in summary_files:
        df = pd.read_csv(summary_file)
        aggregator = {
            col: np.mean if "current" in col else sum for col in df.columns[2:]
        }
        df = df.groupby(["region", "time_stamp"], as_index=False).agg(aggregator)
        dfs.append(df)
        if remove_left_overs:
            summary_file.unlink()
    summary = pd.concat(dfs)
    summary = summary.groupby(["region", "time_stamp"]).sum()
    if save_dir is None:
        save_path = record_path
    else:
        save_path = Path(save_dir)
    full_summary_save_path = save_path / "summary.csv"
    summary.to_csv(full_summary_save_path)


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
                            merged_record.root,
                            dataset.name,
                            description=description,
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
