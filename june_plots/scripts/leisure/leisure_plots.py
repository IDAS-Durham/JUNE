import sys
import numpy as np
from collections import OrderedDict, defaultdict
import yaml
from glob import glob
from scipy import stats
from random import random
import pandas as pd
from tqdm import tqdm
from itertools import chain
import matplotlib.pyplot as plt

from june.utils import parse_age_probabilities
from june.activity import ActivityManager
from june.policy import Policies
from june.groups.leisure import Leisure, generate_leisure_for_config
from june.time import Timer
from june.groups.travel import Travel
from june.simulator import Simulator
from june import paths

config_files_leisure = (paths.configs_path / "defaults/groups/leisure").glob("*.yaml")
simulation_config = paths.configs_path / "config_example.yaml"

# source: private comm with Aoife
time_survey_workdays = {
    "residence": 0.60 + 0.001,
    "work": 0.12,
    "household visits": 0.027,
    "groceries": 0.011,
    "pubs": 0.00887,
    "commute": 0.004 + 0.002 + 0.00075 + 0.0002 + 0.00003,
}
time_survey_workdays["other"] = 1 - sum(time_survey_workdays.values())
time_survey_weekends = {
    "residence": 0.67 + 0.003,
    "work": 0.031712,
    "household visits": 0.046,
    "groceries": 0.015,
    "pubs": 0.015,
    "commute": 0.002 + 0.0014 + 0.00052 + 0.000256 + 0.000105 + 0.000044,
}
time_survey_weekends["other"] = 1 - sum(time_survey_weekends.values())


class LeisurePlots:
    def __init__(self, world):
        self.world = world
        self.leisure = generate_leisure_for_config(
            world=self.world, config_filename=simulation_config
        )
        self.simulator = self.setup_simulator()
        self.timer = self.simulator.timer
        self.activity_manager = self.simulator.activity_manager

    def setup_simulator(self):
        simulator = Simulator.from_file(
            world=self.world,
            policies=Policies([]),
            interaction=None,
            leisure=self.leisure,
            travel=Travel(),
            infection_selector=None,
            infection_seed=None,
            config_filename=simulation_config,
            record=None,
        )
        return simulator

    def simulate_day(self, dates, stop_at_leisure=False):
        time_in_place = {
            "residence": 0,
            "work": 0,
            "household visits": 0,
            "groceries": 0,
            "pubs": 0,
            "commute": 0,
            "other": 0,
        }
        self.timer.reset()
        while str(self.timer.date.date()) not in dates:
            next(self.timer)
        total_duration = 0
        while str(self.timer.date.date()) in dates:
            self.simulator.clear_world()
            self.activity_manager.do_timestep()
            duration = self.timer.duration
            for household in self.world.households:
                residents = 0
                visitors = 0
                for person in household.people:
                    if person.residence.group == household:
                        residents += 1
                    elif person.leisure.group == household:
                        visitors += 1
                    else:
                        raise ValueError
                time_in_place["residence"] += duration * residents
                time_in_place["household visits"] += duration * visitors

            for care_home in self.world.care_homes:
                time_in_place["residence"] += duration * len(care_home.residents)
                time_in_place["work"] += duration * len(care_home.workers)
                time_in_place["other"] += duration * len(care_home.visitors)

            for company in self.world.companies:
                time_in_place["work"] += duration * len(company.people)

            for pub in self.world.pubs:
                time_in_place["pubs"] += duration * len(pub.people)

            for grocery in self.world.groceries:
                time_in_place["groceries"] += duration * len(grocery.people)

            for cinema in self.world.cinemas:
                time_in_place["other"] += duration * len(cinema.people)

            for station in self.world.stations:
                time_in_place["commute"] += duration * sum(
                    len(inter_city_transport.people)
                    for inter_city_transport in station.inter_city_transports
                )

            for city in self.world.cities:
                time_in_place["commute"] += duration * sum(
                    len(city_transport.people)
                    for city_transport in city.city_transports
                )

            for university in self.world.universities:
                time_in_place["work"] += duration * len(university.people)

            for hospital in self.world.hospitals:
                time_in_place["work"] += duration * len(hospital[0].people)

            for school in self.world.schools:
                time_in_place["work"] += duration * len(school.people)
            total_duration += duration
            assert np.isclose(
                total_duration * len(self.world.people),
                sum(time_in_place.values()),
                rtol=0.01,
            )
            next(self.timer)
            if stop_at_leisure:
                if (
                    "leisure" in self.simulator.timer.activities
                    and "primary_activity" not in self.simulator.timer.activities
                ):
                    break
        return time_in_place

    def _normalise_times(self, times):
        # times_normed = {key: value for key, value in times.items() if key != "other"}
        times_normed = (
            times  # {key: value for key, value in times.items() if key != "other"}
        )
        n = sum(times_normed.values())
        return {key: value / n for key, value in times_normed.items()}

    def plot_time_survey(self):
        june_times_weekend = self.simulate_day(["2020-03-01"])
        june_times_workday = self.simulate_day(["2020-03-02"])
        june_times_workday_normed = self._normalise_times(june_times_workday)
        june_times_weekend_normed = self._normalise_times(june_times_weekend)
        time_survey_workdays_normed = self._normalise_times(time_survey_workdays)
        time_survey_weekends_normed = self._normalise_times(time_survey_weekends)
        weekday_ratios = {}
        for key in june_times_workday_normed:
            weekday_ratios[key] = (
                june_times_workday_normed[key] / time_survey_workdays_normed[key]
            )
        weekend_ratios = {}
        for key in june_times_weekend_normed:
            weekend_ratios[key] = (
                june_times_weekend_normed[key] / time_survey_weekends_normed[key]
            )

        fig, ax = plt.subplots(1, 2, sharey=True, figsize=(6, 3))
        ax[0].bar(
            weekday_ratios.keys(), weekday_ratios.values(), alpha=0.8,
        )
        ax[0].set_title("Weekday [JUNE / survey]")
        ax[1].bar(
            weekend_ratios.keys(), weekend_ratios.values(), alpha=0.8,
        )
        ax[1].set_title("Weekend [JUNE / survey]")
        ax[0].set_ylabel("Fraction ratio")
        ax[0].set_xlabel("Activity")
        ax[1].set_xlabel("Activity")
        ax[0].axhline(1, color="black", linestyle="--")
        ax[1].axhline(1, color="black", linestyle="--")
        # ax[0].set_yscale('log')
        # ax[1].set_yscale('log')
        plt.subplots_adjust(wspace=0, hspace=0)
        fig.autofmt_xdate()
        return ax

    def plot_occupancy(self):
        self.simulate_day(dates=["2020-03-01"], stop_at_leisure=True)
        # occupancy
        f, ax = plt.subplots(1, 3, figsize=(8, 2), sharey=True)
        pub_sizes = [pub.size for pub in self.world.pubs]
        grocery_sizes = [grocery.size for grocery in self.world.groceries]
        cinema_sizes = [cinema.size for cinema in self.world.cinemas]
        ax[0].hist(
            pub_sizes, density=True, color="C0", label="pubs/restaurants", bins=50
        )
        ax[1].hist(grocery_sizes, density=True, color="C1", label="stores", bins=50)
        ax[2].hist(cinema_sizes, density=True, label="cinemas", color="C2", bins=50)
        ax[0].legend()
        ax[1].legend()
        ax[2].legend()
        ax[0].set_xlabel("Occupancy")
        ax[1].set_xlabel("Occupancy")
        ax[2].set_xlabel("Occupancy")
        ax[0].set_ylabel("Frequency")
        plt.subplots_adjust(wspace=0, hspace=0)
        return ax

    def plot_social_venues_age_distributions(self):
        self.simulate_day(dates=["2020-03-01"], stop_at_leisure=True)
        f, ax = plt.subplots(1, 3, figsize=(8, 2), sharey=True)
        pub_ages = [person.age for sv in self.world.pubs for person in sv.people]
        grocery_ages = [
            person.age for sv in self.world.groceries for person in sv.people
        ]
        cinema_ages = [person.age for sv in self.world.cinemas for person in sv.people]

        ax[0].hist(
            pub_ages, density=True, color="C0", label="pubs/restaurants", bins=20
        )
        ax[1].hist(grocery_ages, density=True, color="C1", label="stores", bins=20)
        ax[2].hist(cinema_ages, density=True, label="cinemas", color="C2", bins=20)
        ax[0].legend()
        ax[1].legend()
        ax[2].legend()
        ax[0].set_xlabel("Age")
        ax[1].set_xlabel("Age")
        ax[2].set_xlabel("Age")
        ax[0].set_ylabel("Frequency")
        for axis in ax:
            axis.set_xlim(0, 100)
        plt.subplots_adjust(wspace=0, hspace=0)
        return ax

    def _simulate_leisure_week(self, parameter, boost, retired=False):
        """
        Note: Adjust parameters according to config file.
        here we assume 3 hours of leisure a week 
        """
        hist = []
        for _ in range(5000):
            times_a_week = 0
            for _ in range(0, 5):
                if retired:
                    time = 11 / 24
                else:
                    time = 3 / 24
                goes = np.random.poisson(parameter * time)
                if goes > 0:
                    times_a_week += 1
            for _ in range(2):
                for _ in range(3):
                    goes = np.random.poisson(boost * parameter * 4 / 24)
                    if goes > 0:
                        times_a_week += 1
            hist.append(times_a_week)
        return np.array(hist)

    def _get_freqs_grocery(self, parameter, boost, retired=False):
        hist = self._simulate_leisure_week(
            parameter=parameter, boost=boost, retired=retired
        )
        ret = {}
        total = len(hist)
        ret["0"] = np.count_nonzero(hist == 0) / total * 100
        ret["1"] = np.count_nonzero(hist == 1) / total * 100
        ret["2+"] = np.count_nonzero(hist >= 2) / total * 100
        return ret

    def plot_grocery_times_per_week_stata_vs_poisson(self):
        fig, ax = plt.subplots()
        # set width of bar
        barWidth = 0.1
        sim = {
            "18-24": self._get_freqs_grocery(parameter=1.30, boost=1),
            "25-34": self._get_freqs_grocery(parameter=1.50, boost=1),
            "35-44": self._get_freqs_grocery(parameter=1.7, boost=1),
            "45-54": self._get_freqs_grocery(parameter=1.65, boost=1),
            "55-64": self._get_freqs_grocery(parameter=1.65, boost=1),
            "65+": self._get_freqs_grocery(parameter=0.75, boost=1, retired=True),
        }
        data = {
            "18-24": {"0": 14, "1": 28, "2+": 44 + 14},
            "25-34": {"0": 9, "1": 23, "2+": 53 + 15},
            "35-44": {"0": 7, "1": 19, "2+": 57 + 17},
            "45-54": {"0": 7, "1": 21, "2+": 55 + 17},
            "55-64": {"0": 9, "1": 18, "2+": 57 + 16},
            "65+": {"0": 8, "1": 23, "2+": 51 + 18},
        }

        # set height of bar
        sim_bars1 = sim["18-24"].values()
        sim_bars2 = sim["25-34"].values()
        sim_bars3 = sim["35-44"].values()
        sim_bars4 = sim["45-54"].values()
        sim_bars5 = sim["55-64"].values()
        sim_bars6 = sim["65+"].values()

        data_bars1 = data["18-24"].values()
        data_bars2 = data["25-34"].values()
        data_bars3 = data["35-44"].values()
        data_bars4 = data["45-54"].values()
        data_bars5 = data["55-64"].values()
        data_bars6 = data["65+"].values()

        # Set position of bar on X axis

        sim_r1 = np.arange(len(sim_bars1)) + barWidth / 2
        sim_r2 = np.array([x + barWidth for x in sim_r1])
        sim_r3 = [x + barWidth for x in sim_r2]
        sim_r4 = [x + barWidth for x in sim_r3]
        sim_r5 = [x + barWidth for x in sim_r4]
        sim_r6 = [x + barWidth for x in sim_r5]

        data_r1 = np.arange(len(data_bars1))
        data_r2 = [x + barWidth for x in data_r1]
        data_r3 = [x + barWidth for x in data_r2]
        data_r4 = [x + barWidth for x in data_r3]
        data_r5 = [x + barWidth for x in data_r4]
        data_r6 = [x + barWidth for x in data_r5]

        # Make the plot
        ax.bar(
            data_r1,
            data_bars1,
            width=barWidth / 2,
            edgecolor="white",
            label="Statista 18-24",
            color="C1",
        )
        ax.bar(
            data_r2,
            data_bars2,
            width=barWidth / 2,
            edgecolor="white",
            label="Statista 25-34",
            color="C2",
        )
        ax.bar(
            data_r3,
            data_bars3,
            width=barWidth / 2,
            edgecolor="white",
            label="Statista 35-44",
            color="C3",
        )
        ax.bar(
            data_r4,
            data_bars4,
            width=barWidth / 2,
            edgecolor="white",
            label="Statista 45-54",
            color="C4",
        )
        ax.bar(
            data_r5,
            data_bars5,
            width=barWidth / 2,
            edgecolor="white",
            label="Statista 55-64",
            color="C5",
        )
        ax.bar(
            data_r6,
            data_bars6,
            width=barWidth / 2,
            edgecolor="white",
            label="Statista 65+",
            color="C7",
        )

        ax.bar(
            sim_r1,
            sim_bars1,
            width=barWidth / 2,
            edgecolor="white",
            label="JUNE 18-24",
            color="C1",
            alpha=0.5,
        )
        ax.bar(
            sim_r2,
            sim_bars2,
            width=barWidth / 2,
            edgecolor="white",
            label="JUNE 25-34",
            color="C2",
            alpha=0.5,
        )
        ax.bar(
            sim_r3,
            sim_bars3,
            width=barWidth / 2,
            edgecolor="white",
            label="JUNE 35-44",
            color="C3",
            alpha=0.5,
        )
        ax.bar(
            sim_r4,
            sim_bars4,
            width=barWidth / 2,
            edgecolor="white",
            label="JUNE 45-54",
            color="C4",
            alpha=0.5,
        )
        ax.bar(
            sim_r5,
            sim_bars5,
            width=barWidth / 2,
            edgecolor="white",
            label="JUNE 55-64",
            color="C5",
            alpha=0.5,
        )
        ax.bar(
            sim_r6,
            sim_bars6,
            width=barWidth / 2,
            edgecolor="white",
            label="JUNE 65+",
            color="C7",
            alpha=0.5,
        )

        # Add xticks on the middle of the group bars
        ax.set_xlabel("Times a week", fontweight="bold")
        plt.xticks(
            [r + 2.5 * barWidth for r in range(len(sim_bars1))], ["0", "1", "2+"]
        )

        # Create legend & Show graphic
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))
        ax.set_title("Grocery shopping")
        ax.set_ylabel("Percentage [\%]")
        return ax

    def _get_pub_age_group(self, person):
        if person.age < 16:
            return None
        elif person.age < 24:
            return "16-24"
        elif person.age < 44:
            return "25-44"
        elif person.age < 64:
            return "45-64"
        elif person.age < 74:
            return "65-74"
        else:
            return "75+"

    def plot_people_going_to_the_pub(self):
        self.simulate_day(["2020-03-01"], stop_at_leisure=True)
        data = {"16-24": 55.7, "25-44": 59.3, "45-64": 54.5, "65-74": 45, "75+": 31}
        in_pubs = {"16-24": 0, "25-44": 0, "45-64": 0, "65-74": 0, "75+": 0}
        total = {"16-24": 0, "25-44": 0, "45-64": 0, "65-74": 0, "75+": 0}
        for pub in self.world.pubs:
            for person in pub.people:
                age_group = self._get_pub_age_group(person)
                if not age_group:
                    continue
                in_pubs[age_group] += 1
        for person in self.world.people:
            if person.leisure is not None:
                age_group = self._get_pub_age_group(person)
                if not age_group:
                    continue
                total[age_group] += 1

        june_ratios = {}
        for key in total:
            june_ratios[key] = in_pubs[key] / total[key] * 100

        f, ax = plt.subplots()
        ax.bar(data.keys(), data.values(), label="data", alpha=0.5)
        ax.bar(june_ratios.keys(), june_ratios.values(), label="JUNE", alpha=0.5)
        ax.set_xlabel("Age bracket")
        ax.set_ylabel("Percentage of population [\%]")
        ax.legend()
        return ax

    def plot_people_going_groceries(self):
        self.simulate_day(["2020-03-01"], stop_at_leisure=True)
        # data = {"16-24": 55.7, "25-44": 59.3, "45-64": 54.5, "65-74": 45, "75+": 31}
        in_pubs = {"16-24": 0, "25-44": 0, "45-64": 0, "65-74": 0, "75+": 0}
        total = {"16-24": 0, "25-44": 0, "45-64": 0, "65-74": 0, "75+": 0}
        for pub in self.world.groceries:
            for person in pub.people:
                age_group = self._get_pub_age_group(person)
                if not age_group:
                    continue
                in_pubs[age_group] += 1
        for person in self.world.people:
            if person.leisure is not None:
                age_group = self._get_pub_age_group(person)
                if not age_group:
                    continue
                total[age_group] += 1

        june_ratios = {}
        for key in total:
            june_ratios[key] = in_pubs[key] / total[key] * 100

        f, ax = plt.subplots()
        ax.bar(june_ratios.keys(), june_ratios.values(), label="JUNE")
        ax.set_xlabel("Age bracket")
        ax.set_ylabel("Percentage of population [\%]")
        ax.legend()
        return ax

    def plot_leisure_type_by_age(self):
        self.simulate_day(["2020-03-01"], stop_at_leisure=True)
        ages = np.arange(0, 100)
        venue_types = {
            vtype: {age: 0 for age in ages}
            for vtype in ["pub", "grocery", "household", "cinema", "care_home", "None"]
        }
        people_per_age = np.zeros(100)
        for person in self.world.people:
            people_per_age[person.age] += 1
            if person.leisure is not None:
                venue_types[person.leisure.group.spec][person.age] += 1
            else:
                venue_types["None"][person.age] += 1
        venue_types = pd.DataFrame.from_dict(venue_types)
        venue_types = venue_types / venue_types.sum(axis=0)
        totals = [
            i + j + k + l + m + n
            for i, j, k, l, m, n in zip(
                venue_types["pub"],
                venue_types["grocery"],
                venue_types["household"],
                venue_types["cinema"],
                venue_types["care_home"],
                venue_types["None"],
            )
        ]
        # plot
        barWidth = 1.1
        r = np.arange(0, 100)
        # data bars
        data_bars = {}
        for key in venue_types:
            data_bars[key] = [i / j * 100 for i, j in zip(venue_types[key], totals)]
        f, ax = plt.subplots()
        ax.bar(
            r,
            data_bars["pub"],
            color="C0",
            width=barWidth,
            label="pubs/restaurants",
            align="center",
        )
        ax.bar(
            r,
            data_bars["grocery"],
            bottom=data_bars["pub"],
            color="C1",
            align="center",
            width=barWidth,
            label="shopping",
        )
        ax.bar(
            r,
            data_bars["household"],
            bottom=[i + j for i, j in zip(data_bars["pub"], data_bars["grocery"])],
            color=f"C2",
            align="center",
            width=barWidth,
            label="household visits",
        )
        ax.bar(
            r,
            data_bars["cinema"],
            bottom=[
                i + j + k
                for i, j, k in zip(
                    data_bars["pub"], data_bars["grocery"], data_bars["household"]
                )
            ],
            color="C3",
            align="center",
            width=barWidth,
            label="cinema",
        )
        ax.bar(
            r,
            data_bars["care_home"],
            bottom=[
                i + j + k + l
                for i, j, k, l in zip(
                    data_bars["pub"],
                    data_bars["grocery"],
                    data_bars["household"],
                    data_bars["cinema"],
                )
            ],
            color="C4",
            align="center",
            width=barWidth,
            label="care home",
        )
        ax.bar(
            r,
            data_bars["None"],
            bottom=[
                i + j + k + l + m
                for i, j, k, l, m in zip(
                    data_bars["pub"],
                    data_bars["grocery"],
                    data_bars["household"],
                    data_bars["cinema"],
                    data_bars["care_home"],
                )
            ],
            color="C5",
            align="center",
            width=barWidth,
            label="None",
        )
        ax.legend()
        ax.set_xlabel("Age")
        ax.set_ylabel("Percentage population")
        ax.set_xlim(0,100)
        ax.set_ylim(0,100)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        return ax
