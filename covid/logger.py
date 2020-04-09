"""
Class to log all important information at each timestep.
"""
import json

class Logger:

    def __init__(self, world, save_path = "results.json"):
        self.world = world
        self.data_dict = {}
        self.save_path = save_path

    def log_timestep(self, day, dayshift):
        if day not in self.data_dict:
            self.data_dict[day] = {}
        self.data_dict[day][dayshift] = {}
        for area in self.world.areas.members:
            susceptible, infected, recovered = self.get_infected_people_area(area)
            self.data_dict[day][dayshift]["susceptible"] = susceptible
            self.data_dict[day][dayshift]["infected"] = infected 
            self.data_dict[day][dayshift]["recovered"] = recovered 
        with open(self.save_path, "w") as f:
            json.dump(self.data_dict, f)

    def get_infected_people_area(self, area):
        infected = 0
        susceptible = 0
        recovered = 0
        for person in area.people:
            if person.is_suceptible():
                susceptible += 1
            if person.is_infected():
                infected += 1
            if person.is_recovered():
                recovered += 1
        return susceptible, infected, recovered





