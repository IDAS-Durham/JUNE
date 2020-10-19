import sys
import numpy as np
from collections import OrderedDict, defaultdict
import yaml
from glob import glob
from scipy import stats
from random import random
from tqdm import tqdm
import matplotlib.pyplot as plt

from june.utils import parse_age_probabilities
from june import paths

config_files_leisure = (paths.configs_path / "defaults/groups/leisure").glob("*.yaml")

class LeisurePlots:

    def __init__(self, world, colors):
        self.world = world
        self.colors = colors

    def run_poisson_process(
            self,
    ):
        probabilities_dict = parse_multiple_config_files()
        self.time_spent_in_leisure, self.ret_child, self.ret_adult, self.ret_retired = simulate_leisure_week(probabilities_dict)

    def plot_week_probabilities(
            self,
    ):
        "Plotting probabaility of doing different activities in a week"

        activities = []
        new_activities = []
        child_probability = []
        adult_probability = []
        retired_probability = []
        for activity in self.ret_adult:
            activities.append(activity)
            new_activities.append(activity.replace("_", " "))
            adult_probability.append(self.ret_adult[activity])
            try:
                child_probability.append(self.ret_child[activity])
            except:
                child_probability.append(0.)
            retired_probability.append(self.ret_retired[activity])

        x = np.arange(len(activities))  # the label locations
        width = 0.35  # the width of the bars

        f, ax = plt.subplots()
        ax.bar(x - width/2, child_probability, width/2, label = 'Children')
        ax.bar(x, adult_probability, width/2, label = 'Adults')
        ax.bar(x + width/2, retired_probability, width/2, label = 'Retired')
        ax.set_ylabel('Probability of doing activity in a week')
        ax.set_xticks(x)
        ax.set_xticklabels(new_activities)
        ax.legend()
        plt.xticks(rotation=45)

        return ax

    def plot_leisure_time_spent(
            self
    ):
        "Plotting time spent in leisure by age"
        
        f, ax = plt.subplots()
        ax.bar(self.time_spent_in_leisure.keys(), self.time_spent_in_leisure.values(), color=self.colors['JUNE'])
        ax.axvline(65, color = "red", linestyle=":")
        ax.set_ylabel("Hours of leisure a week")
        ax.set_xlabel("Age")

        return ax

def parse_config_file(config_file_path):
    with open(config_file_path) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    male_age_probabilities = parse_age_probabilities(config["male_age_probabilities"])
    female_age_probabilities = parse_age_probabilities(
        config["female_age_probabilities"]
    )
    return male_age_probabilities, female_age_probabilities

def parse_config_file(config_file_path):
    with open(config_file_path) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    male_age_probabilities = parse_age_probabilities(config["male_age_probabilities"])
    female_age_probabilities = parse_age_probabilities(
        config["female_age_probabilities"]
    )
    return male_age_probabilities, female_age_probabilities


def parse_multiple_config_files(config_files=config_files_leisure):

    probabilities_dict = OrderedDict()
    for config_path in config_files:
        name = config_path.name.split("/")[-1].split(".")[0]
        probabilities_dict[name] = {}
        (
            probabilities_dict[name]["m"],
            probabilities_dict[name]["f"],
        ) = parse_config_file(config_path)
    return probabilities_dict


def simulate_poisson_process(
    probabilities_dict, leisure_delta_t
):
    activities = list(probabilities_dict.keys())
    does_activity_age = {}
    for age in np.arange(0, 100):
        poisson_parameters = [
            probabilities_dict[activity]["m"][age] for activity in activities
        ]
        total_poisson = sum(poisson_parameters)
        does_activity = random() < (1 - np.exp(-total_poisson * leisure_delta_t))
        if does_activity:
            which_activity = np.random.choice(
                activities, p=np.array(poisson_parameters) / np.sum(poisson_parameters)
            )
            does_activity_age[age] = which_activity
        else:
            does_activity_age[age] = None
    return does_activity_age

def simulate_leisure_week(probabilities_dict):
    weekday_leisure_workers = [3]
    weekday_leisure_retired = [8, 3]
    weekend_leisure = [4,4,4]
    time_spent_in_leisure = defaultdict(list)
    child_activities = defaultdict(list)
    adult_activities = defaultdict(list)
    retired_activities = defaultdict(list)
    
    ages = np.arange(0,100)
    for i in tqdm(range(50)):
        time_spent_in_leisure_week = defaultdict(int)
        child_activities_week = defaultdict(int)
        adult_activities_week = defaultdict(int)
        retired_activities_week = defaultdict(int)
        for _ in range(5):
            for age in ages:
                if age < 65:
                    weekday_leisure = weekday_leisure_workers
                else:
                    weekday_leisure = weekday_leisure_retired
                for dt in weekday_leisure:
                    activities_age = simulate_poisson_process(probabilities_dict, dt / 24)
                    if activities_age[age] is not None:
                        time_spent_in_leisure_week[age] += dt
                        if age < 19:
                            child_activities_week[activities_age[age]] += 1
                        elif age >= 19 and age < 65:
                            adult_activities_week[activities_age[age]] += 1
                        else:
                            retired_activities_week[activities_age[age]] += 1

        for _ in range(2):
            for dt in weekend_leisure:
                activities_age = simulate_poisson_process(probabilities_dict, dt / 24)
                for age in ages:
                    if activities_age[age] is not None:
                        time_spent_in_leisure_week[age] += dt
                        if age < 19:
                            child_activities_week[activities_age[age]] += 1
                        elif age >= 19 and age < 65:
                            adult_activities_week[activities_age[age]] += 1
                        else:
                            retired_activities_week[activities_age[age]] += 1
                        
        for age in activities_age:
            time_spent_in_leisure[age].append(time_spent_in_leisure_week[age])
        for activity in child_activities_week:
            child_activities[activity].append(child_activities_week[activity]/(7*19))
        for activity in adult_activities_week:
            adult_activities[activity].append(adult_activities_week[activity]/(7*47))
        for activity in retired_activities_week:
            retired_activities[activity].append(retired_activities_week[activity]/(7*36))
        
    ret = defaultdict(float)
    for age in activities_age:
        ret[age] = np.mean(time_spent_in_leisure[age])
    ret_child = defaultdict(float)
    for activity in child_activities:
        ret_child[activity] = np.mean(child_activities[activity])
    ret_adult = defaultdict(float)
    for activity in adult_activities:
        ret_adult[activity] = np.mean(adult_activities[activity])
    ret_retired = defaultdict(float)
    for activity in retired_activities:
        ret_retired[activity] = np.mean(retired_activities[activity])
    return ret, ret_child, ret_adult, ret_retired
