import pandas as pd
import numpy as np
from pathlib import Path
import json


class Logger:
    def __init__(
        self,
        timer,
        age_range=[0, 5, 19, 30, 65, 100],
        infection_keys=[
            "infected",
            "recovered",
            "susceptible",
            "hospitalised",
            "intensive_care",
        ],
        save_path="results",
    ):
        self.timer = timer
        self.output_dict = {}
        self.age_range = age_range
        self.infection_keys = infection_keys
        self.save_path = save_path

    def initialize_logging_dict(self):
        return dict.fromkeys(self.infection_keys, 0)

    def initialize_age_dict(self):
        age_dict = {
            "{}-{}".format(
                self.age_range[i], self.age_range[i + 1] - 1
            ): self.initialize_logging_dict()
            for i, age in enumerate(self.age_range[:-1])
        }
        self.age_keys = list(age_dict.keys())
        return age_dict

    def initialize_area_dict(self, areas):
        area_dict = {}
        for area in areas:
            area_dict[area.name] = {
                "f": self.initialize_age_dict(),
                "m": self.initialize_age_dict(),
            }
        return area_dict

    def log_timestep(self, time_stamp, areas, save=False):
        time_stamp = time_stamp.strftime('%Y-%m-%dT%H:%M:%S.%f')
        self.output_dict[time_stamp] = self.initialize_area_dict(
            areas, 
        )
        for area in areas.members:
            self.log_area(
                area, self.output_dict[time_stamp][area.name],
            )
        if save:
            json_path = Path(self.save_path) / "data.json"
            with open(json_path, "w") as f:
                json.dump(self.output_dict, f)

    def log_area(self, area, area_dict):
        for person in area.people:
            self.log_person(person, area_dict)

    def log_person(self, person, area_dict):
        age_key = self.get_age_key(person.age)
        personal_infection_keys = self.get_infection_key(person)
        for infection_key in personal_infection_keys:
            area_dict[person.sex][age_key][infection_key] += 1

    def get_age_key(self, age):
        age_bin = np.digitize(age, self.age_range) - 1
        return self.age_keys[age_bin]

    def get_infection_key(self, person):
        personal_keys = []
        for key in self.infection_keys:
            if getattr(person, key):
                personal_keys.append(key)
        return personal_keys

    """
    def initialize_column_names(self, logging_options, sex, age_ranges):
        column_names = [] 
        for logging_option in logging_options:
            for s in sex:
                for age_range in age_ranges:
                    column_names.append(f'{logging_option}_{s}_{age_range[0]}_{age_range[1]}')
        column_names.insert(0,'time_stamp')
        return column_names

    
    def initialize_dataframe(self, logging_options, sex, age_ranges):
        column_names = self.initialize_column_names(logging_options, sex, age_ranges)
        return pd.DataFrame(columns = column_names)
    """
