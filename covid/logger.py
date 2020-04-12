"""
Class to log all important information at each timestep.
"""
import json
import os
import matplotlib.pyplot as plt


class Logger:
    def __init__(self, world, save_path="results"):
        self.world = world
        self.data_dict = {}
        self.save_path = save_path
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

    def log_timestep(self, day, dayshift):
        if day not in self.data_dict:
            self.data_dict[day] = {}
        self.data_dict[day][dayshift] = {}
        for area in self.world.areas.members:
            susceptible, infected, recovered = self.get_infected_people_area(area)
            self.data_dict[day][dayshift]["susceptible"] = susceptible
            self.data_dict[day][dayshift]["infected"] = infected
            self.data_dict[day][dayshift]["recovered"] = recovered
        json_path = os.path.join(self.save_path, "data.json")
        with open(json_path, "w") as f:
            json.dump(self.data_dict, f)

    def get_infected_people_area(self, area):
        infected = 0
        susceptible = 0
        recovered = 0
        for person in area.people:
            if person.is_susceptible():
                susceptible += 1
            if person.is_infected():
                infected += 1
            if person.is_recovered():
                recovered += 1
        return susceptible, infected, recovered

    def plot_infection_curves_per_day(self):
        infected = []
        susceptible = []
        recovered = []
        day_array = []
        for day in self.data_dict.keys():
            day_array.append(day)
            n_inf = sum(
                [
                    self.data_dict[day][shift]["susceptible"]
                    for shift in self.data_dict[day].keys()
                ]
            )
            n_susc = sum(
                [
                    self.data_dict[day][shift]["susceptible"]
                    for shift in self.data_dict[day].keys()
                ]
            )
            n_rec = sum(
                [
                    self.data_dict[day][shift]["recovered"]
                    for shift in self.data_dict[day].keys()
                ]
            )
            infected.append(n_inf)
            susceptible.append(n_susc)
            recovered.append(n_rec)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(day_array, infected, label="Infected")
        ax.plot(day_array, susceptible, label="Susceptible", linestyle="--")
        ax.plot(day_array, recovered, label="Recovered", linestyle=":")
        ax.set_xlabel("Days")
        ax.set_ylabel("Number of people")
        ax.set_title("Infection curves")
        fig.savefig(os.path.join(self.save_path, "infection_curves.png"), dpi=300)





