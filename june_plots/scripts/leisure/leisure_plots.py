import pandas as pd
import numpy as np
import yaml
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path
from collections import defaultdict

plt.style.use(["science"])
plt.style.reload_library()

from june.groups.leisure import (
    PubDistributor,
    CinemaDistributor,
    GroceryDistributor,
    GymDistributor,
    ResidenceVisitsDistributor,
    Leisure,
)
from june import paths

config_files_leisure = list(
    (paths.configs_path / "defaults/groups/leisure").glob("*.yaml")
)

_sex_dict = {"male": "m", "female": "f"}


def _reverse_interval(interval):
    return f"{interval.left}-{interval.right}"


def convert_interval(interval):
    age1, age2 = list(map(int, interval.split("-")))
    return pd.Interval(left=age1, right=age2 - 1, closed="both")


class LeisurePlots:
    def __init__(self):
        leisure_distributors = {
            "pubs": PubDistributor.from_config(social_venues=None),
            "groceries": GroceryDistributor.from_config(social_venues=None),
            "cinemas": CinemaDistributor.from_config(social_venues=None),
            "gyms": GymDistributor.from_config(social_venues=None),
            "residence_visits": ResidenceVisitsDistributor.from_config(),
        }
        self.leisure = Leisure(leisure_distributors=leisure_distributors)
        age_edges = [0, 9, 15, 19, 31, 51, 66, 86]
        self.age_bins = [
            pd.Interval(left=age_edges[i], right=age_edges[i + 1] - 1, closed="both")
            for i in range(len(age_edges) - 1)
        ] + [pd.Interval(left=86, right=99, closed="both")]

    def get_data_dfs(self, day_type, sex):
        ret_times = pd.DataFrame(index=self.age_bins)
        if day_type == "weekday":
            n_days = 5
        else:
            n_days = 2
        for config_file in config_files_leisure:
            name = Path(config_file).name.split(".")[0]
            if name == "visits":
                name = "residence_visits"
            with open(config_file) as f:
                config = yaml.load(f, Loader=yaml.FullLoader)
                times_per_week = config["times_per_week"][day_type][sex]
                hours_per_day = config["hours_per_day"][day_type][sex]
                for _age_bin, value in times_per_week.items():
                    age_bin = convert_interval(_age_bin)
                    ret_times.loc[age_bin, name] = value
        return ret_times

    def get_june_dfs(self, day_type, sex):
        ret_times = pd.DataFrame(index=self.age_bins)
        ret_hours = pd.DataFrame(index=self.age_bins)
        for age_bin in self.age_bins:
            age = int(0.5 * (age_bin.left + age_bin.right))
            prob_dict = defaultdict(float)
            hours_dict = defaultdict(float)
            if day_type == "weekday":
                n_days = 5
                if age >= 65:
                    morning_prob = self.get_activity_probabilities(
                        age=age,
                        sex=sex,
                        is_weekend=False,
                        working_hours=True,
                        delta_time=8 / 24,
                    )
                    for activity, value in morning_prob.items():
                        prob_dict[activity] += value * 5  # mo-fri
                        hours_dict[activity] += value * 5 * 8
                afternoon_prob = self.get_activity_probabilities(
                    age=age,
                    sex=sex,
                    is_weekend=False,
                    working_hours=False,
                    delta_time=3 / 24,
                )
                for activity, value in afternoon_prob.items():
                    prob_dict[activity] += value * 5  # mo-fri
                    hours_dict[activity] += value * 5 * 3
            else:
                n_days = 2
                for _ in range(3):  # 3 leisure time steps per weekend
                    ts_prob = self.get_activity_probabilities(
                        age=age,
                        sex=sex,
                        is_weekend=True,
                        working_hours=False,
                        delta_time=4 / 24,
                    )
                    for activity, value in ts_prob.items():
                        prob_dict[activity] += value * 2  # saturday and sunday
                        hours_dict[activity] += value * 2 * 4
            for activity, value in prob_dict.items():
                ret_times.loc[age_bin, activity] = value
            for activity, value in hours_dict.items():
                ret_hours.loc[age_bin, activity] = value
        return ret_times, ret_hours

    def get_activity_probabilities(
        self, age, sex, is_weekend, delta_time, working_hours
    ):
        sex = _sex_dict[sex]
        prob_dict = self.leisure.get_leisure_probability_for_age_and_sex(
            age=age,
            sex=sex,
            is_weekend=is_weekend,
            working_hours=working_hours,
            delta_time=delta_time,
            regional_compliance=1,
        )
        ret = {}
        does_activity = prob_dict["does_activity"]
        for activty, share in prob_dict["activities"].items():
            ret[activty] = share * does_activity
        return ret

    def get_toplot(self, day_type, sex):
        data_df = self.get_data_dfs(day_type=day_type, sex=sex)
        june_df, _ = self.get_june_dfs(day_type=day_type, sex=sex)
        june_df = june_df.loc[:, [column for column in data_df.columns]]
        data_df = data_df.rename(_reverse_interval)
        june_df = june_df.rename(_reverse_interval)
        june_df = june_df.rename(columns={"residence_visits": "residence visits"})
        data_df = data_df.rename(columns={"residence_visits": "residence visits"})
        june_df = june_df.loc[
            :, ["pubs", "groceries", "cinemas", "residence visits", "gyms"]
        ]
        data_df = data_df.loc[
            :, ["pubs", "groceries", "cinemas", "residence visits", "gyms"]
        ]
        return june_df, data_df

    def plot_times_per_week_comparison_single(
        self, day_type, sex, ax=None, legend=True
    ):
        if ax is None:
            fig, ax = plt.subplots()
        toplot_june, toplot_data = self.get_toplot(day_type=day_type, sex=sex)
        positions = np.arange(len(toplot_data.index)) + 0.15
        width = 0.35
        xtra_space = 0.05
        bottom_june = np.zeros(len(toplot_june.index))
        bottom_data = np.zeros(len(toplot_june.index))
        for i, column in enumerate(toplot_june.columns):
            ax.bar(
                positions,
                toplot_june[column],
                width=width,
                bottom=bottom_june,
                color=f"C{i}",
                label=f"{column} JUNE",
            )
            ax.bar(
                positions + width + xtra_space,
                toplot_data[column],
                bottom=bottom_data,
                width=width,
                color=f"C{i}",
                label=f"{column} data",
                alpha=0.7,
            )
            bottom_june += toplot_june[column]
            bottom_data += toplot_data[column]
        if legend:
            ax.legend(title="Leisure Activity")
        major_tick_positions = []
        major_tick_labels = []
        for i, position in enumerate(positions):
            major_tick_positions.append(position + (width + xtra_space) / 2)
            major_tick_labels.append(toplot_june.index[i])
        ax.set_xticks(major_tick_positions)
        ax.xaxis.set_ticklabels(major_tick_labels)
        ax.tick_params(axis="x", which="major")
        ax.set_xlabel("Age range")
        ax.set_title(f"{day_type} {sex}")
        return ax

    def plot_times_per_week_comparison(self):
        fig, ax = plt.subplots(2, 2, figsize=(10, 10))
        for i, day_type in enumerate(["weekday", "weekend"]):
            for j, sex in enumerate(["male", "female"]):
                self.plot_times_per_week_comparison_single(
                    ax=ax[i, j], day_type=day_type, sex=sex, legend=False
                )
                ax[i, j].set_ylabel("Times")
                handles, labels = ax[i, j].get_legend_handles_labels()
        fig.legend(handles, labels, loc="center left", bbox_to_anchor=(0.92, 0.5))
        plt.subplots_adjust(wspace=0.2, hspace=0.5)
        return fig, ax

    def plot_leisure_hours_per_week(self):
        ret = None
        for i, day_type in enumerate(["weekday", "weekend"]):
            #for j, sex in enumerate(["male", "female"]):
            if ret is None:
                _, ret = self.get_june_dfs(day_type=day_type, sex="male")
            else:
                _, hours = self.get_june_dfs(day_type=day_type, sex="male")
                ret += hours
        ret["total"] = ret.sum(axis=1)
        ret = ret.rename(_reverse_interval)
        ret = ret.rename(columns={"residence_visits" : "residence visits"})
        ax = ret.plot.bar(
            xlabel="Age range", ylabel="Hours", title="Hours of leisure per week"
        )
        ax.axhline(8.6, linestyle="--", color = "C0", alpha=0.5, label= "ONS average")
        ax.legend(loc="center left", bbox_to_anchor=(1,0.5))
        return ax.get_figure(), ax


if __name__ == "__main__":
    leisure_plots = LeisurePlots()
    fig, ax = leisure_plots.plot_times_per_week_comparison()
    fig.savefig("leisure_comparison.pdf", bbox_inches="tight", dpi=300)
    plt.show()
    fig, ax = leisure_plots.plot_leisure_hours_per_week()
    fig.savefig("leisure_hours_per_week.pdf", bbox_inches="tight", dpi=300)
    plt.show()
