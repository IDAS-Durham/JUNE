import pandas as pd
import matplotlib.pyplot as plt
from june import paths
from collections import defaultdict

default_care_home_age_filename = paths.data_path / "plotting/care_home_data.xlsx"


class CareHomePlots:
    def __init__(self, world):
        self.world = world

    def load_care_home_data(
        self, care_home_age_filename=default_care_home_age_filename
    ):
        care_home_df = pd.read_excel(
            care_home_age_filename,
            sheet_name="Table 1",
            usecols="B:E",
            skiprows=3,
            nrows=8,
            index_col=0,
        )
        non_care_home_df = pd.read_excel(
            care_home_age_filename,
            sheet_name="Table 1",
            usecols="B:E",
            skiprows=11,
            names=["Age group", "Persons", "Males", "Females"],
            nrows=8,
            index_col=0,
        )
        self.percent = 100 * care_home_df / non_care_home_df

    def count_in_interval(self, sex_dict, age_interval):
        result = 0
        for key, value in sex_dict.items():
            if key > age_interval[0] and key < age_interval[1]:
                result += value
        return result

    def plot_age_distribution(self):

        males_care_home = defaultdict(int)
        females_care_home = defaultdict(int)
        males = defaultdict(int)
        females = defaultdict(int)
        for person in self.world.people:
            if person.residence.group.spec == "care_home":
                if person.sex == "m":
                    males_care_home[person.age] += 1
                else:
                    females_care_home[person.age] += 1
            if person.sex == "m":
                males[person.age] += 1
            else:
                females[person.age] += 1
        age_intervals = []
        for name in self.percent.index:
            if name == "85 and over":
                age_intervals.append([85, 150])
            else:
                interval = [int(value) for value in name.split(" to ")]
                age_intervals.append(interval)
        june_percent = self.percent.copy()
        for age_interval in age_intervals:
            care_home_males_interval = self.count_in_interval(
                males_care_home, age_interval
            )
            all_males_interval = self.count_in_interval(males, age_interval)
            care_home_females_interval = self.count_in_interval(
                females_care_home, age_interval
            )
            all_females_interval = self.count_in_interval(females, age_interval)
            if age_interval[0] == 85:
                loc_str = "85 and over"
            else:
                loc_str = f"{age_interval[0]} to {age_interval[1]}"
            june_percent.loc[loc_str, "Males"] = (
                care_home_males_interval / all_males_interval * 100
            )
            june_percent.loc[loc_str, "Females"] = (
                care_home_females_interval / all_females_interval * 100
            )
            june_percent.loc[loc_str, "Persons"] = (
                (care_home_females_interval + care_home_males_interval)
                / (all_females_interval + all_males_interval)
                * 100
            )

        f, ax = plt.subplots()
        self.percent["Persons"].plot.bar(ax=ax, label="NOMIS")
        june_percent["Persons"].plot.bar(ax=ax, alpha=0.5, label="JUNE")
        ax.set_ylabel("Percentage of population in care homes")
        ax.legend()
        return ax
