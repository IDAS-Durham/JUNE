import sys
import numpy as np
from collections import OrderedDict, defaultdict
import yaml
from glob import glob
from scipy import stats
from random import random
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
time_survey = {
    "residence": 0.635 + 0.002,
    "work": 0.08,
    "household visits": 0.034,
    "groceries": 0.013,
    "pubs": 0.012,
    "commute": 0.003 + 0.001 + 0.00064 + 0.0004 + 0.0002 + 0.000157 + 0.000032,
}
time_survey["other"] = 1 - sum(time_survey.values())

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

    def simulate_weekend_and_weekday(self, one_time = False):
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
        total_duration = 0
        while str(self.timer.date.date()) in ["2020-03-01", "2020-03-02"]:
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
            if one_time:
                break
        return time_in_place

    def _normalise_times(self, times):
        times_normed = {key: value for key,value in times.items() if key != "other"}
        n = sum(times_normed.values())
        return  {key : value / n * 100 for key, value in times_normed.items()}

    def plot_time_survey(self):
        june_times = self.simulate_weekend_and_weekday()
        june_times_normed = self._normalise_times(june_times)
        time_survey_normed = self._normalise_times(time_survey)

        fig, ax = plt.subplots()
        ax.bar(time_survey_normed.keys(), time_survey_normed.values(), alpha=0.7, label = "Time Survey")
        ax.bar(june_times_normed.keys(), june_times_normed.values(), alpha=0.7, label = "JUNE")
        ax.set_ylabel("Fraction of time [\%]")
        ax.set_xlabel("Activity")
        fig.autofmt_xdate()
        return ax

    def plot_occupancy(self):
        self.simulate_weekend_and_weekday(one_time=True)
        # occupancy
        f, ax = plt.subplots(1,3, figsize=(8,2), sharey=True) 
        pub_sizes = [pub.size for pub in self.world.pubs]
        grocery_sizes = [grocery.size for grocery in self.world.groceries]
        cinema_sizes = [cinema.size for cinema in self.world.cinemas]
        ax[0].hist(pub_sizes, density=True, color="C0", label="pubs/restaurants")
        ax[1].hist(grocery_sizes, density=True, color="C1", label="stores")
        ax[2].hist(cinema_sizes, density=True, label="cinemas", color="C2")
        ax[0].legend()
        ax[1].legend()
        ax[2].legend()
        ax[0].set_xlabel("Occupancy")
        ax[1].set_xlabel("Occupancy")
        ax[2].set_xlabel("Occupancy")
        ax[0].set_ylabel("Frequency")
        plt.subplots_adjust(wspace=0, hspace=0)
        return ax
