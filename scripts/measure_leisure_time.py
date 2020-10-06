import sys
import numpy as np
from collections import OrderedDict, defaultdict
import yaml
from glob import glob
from scipy import stats
from random import random
import matplotlib.pyplot as plt

from june.utils import parse_age_probabilities
from june import paths

config_files_leisure = (paths.configs_path / "defaults/groups/leisure").glob("*.yaml")


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
    ages = np.arange(0,100)
    for _ in range(100):
        time_spent_in_leisure_week = defaultdict(int)
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

        for _ in range(2):
            for dt in weekend_leisure:
                activities_age = simulate_poisson_process(probabilities_dict, dt / 24)
                for age in ages:
                    if activities_age[age] is not None:
                        time_spent_in_leisure_week[age] += dt
        for age in activities_age:
            time_spent_in_leisure[age].append(time_spent_in_leisure_week[age])
    ret = defaultdict(float)
    for age in activities_age:
        ret[age] = np.mean(time_spent_in_leisure[age])
    return ret



if __name__ == "__main__":
    probabilities_dict = parse_multiple_config_files()
    time_spent_in_leisure = simulate_leisure_week(probabilities_dict)
    plt.bar(time_spent_in_leisure.keys(), time_spent_in_leisure.values())
    plt.axvline(65, color = "red", linestyle=":")
    plt.ylabel("hours of leisure a week")
    plt.xlabel("age")
    plt.show()
