"""
Class to log all important information at each timestep.
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt

# TODO: Change the logger to only use hours and not fractions of days

class Logger:
    def __init__(self, simulator, world, timer, save_path="results"):
        self.simulator = simulator
        self.world = world
        self.timer = timer
        self.data_dict = {}
        self.save_path = save_path
        self.box_mode = self.world.box_mode
        self.age_ranges = [[0, 4], [5, 18], [19, 29], [30, 64], [65, 99]]
        self.total_people_per_area = self.total_people_per_area_by_age_range()
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)
        self.init_logger()


    def init_logger(self):
        keys = ["susceptible", "infected", "recovered", "cumulative_infected"]
        if not self.box_mode:
            for area in self.world.areas.members:
                self.data_dict[area.name] = {}
        self.data_dict["world"] = {}
        self.data_dict["ByAge"] = {'{}-{}'.format(ages[0], ages[1]): {key: {} for key in keys} for ages in self.age_ranges}


    def group_by_age(self, day, area, ages, susceptible, infected, recovered):
        label = "{}-{}".format(ages[0], ages[1])
        susceptible_per_area = sum([susceptible[k] for k in susceptible.keys() if (k >= ages[0] and k <= ages[1])])
        infected_per_area = sum([infected[k] for k in infected.keys() if (k >= ages[0] and k <= ages[1])])
        recovered_per_area = sum([recovered[k] for k in recovered.keys() if (k >= ages[0] and k <= ages[1])])

        if day in self.data_dict["ByAge"][label]["susceptible"]:
            self.data_dict["ByAge"][label]["susceptible"][day] += susceptible_per_area
        else:
            self.data_dict["ByAge"][label]["susceptible"][day] = susceptible_per_area
        
        if day in self.data_dict["ByAge"][label]["infected"]:
            self.data_dict["ByAge"][label]["infected"][day] += infected_per_area
        else:
            self.data_dict["ByAge"][label]["infected"][day] = infected_per_area

        if day in self.data_dict["ByAge"][label]["recovered"]:
            self.data_dict["ByAge"][label]["recovered"][day] += recovered_per_area
        else:
            self.data_dict["ByAge"][label]["recovered"][day] = recovered_per_area

        if day in self.data_dict["ByAge"][label]["cumulative_infected"]:
            self.data_dict["ByAge"][label]["cumulative_infected"][day] += (self.total_people_per_area[area.name][label] - susceptible_per_area)
            # print(self.data_dict["ByAge"][label]["cumulative_infected"][day])
        else:
            self.data_dict["ByAge"][label]["cumulative_infected"][day] = (self.total_people_per_area[area.name][label] - susceptible_per_area)


    def log_timestep(self, day):
        susceptible_world = 0
        infected_world = 0
        recovered_world = 0
        total_people = self.world.people.total_people
        if not self.box_mode:
            for area in self.world.areas.members:
                susceptible, infected, recovered = self.get_infected_people_area(area)
                susceptible_world += sum(susceptible.values())
                infected_world += sum(infected.values())
                recovered_world += sum(recovered.values())
                self.data_dict[area.name][day] = {
                        "susceptible": sum(susceptible.values()),
                        "infected": sum(infected.values()),
                        "recovered": sum(recovered.values()),
                        }
                
                for ages in self.age_ranges:
                    self.group_by_age(day, area, ages, susceptible, infected, recovered)

            self.data_dict["world"][day] = {
                    "susceptible": susceptible_world,
                    "infected": infected_world,
                    "recovered": recovered_world,
                    "cumulative_infected": total_people - susceptible_world
                    }
            self.log_r0()
        else:
            box = self.world.boxes.members[0]
            self.data_dict["world"][day] = {
                    "susceptible": len(self.world.people.susceptible),
                    "infected": len(self.world.people.infected),
                    "recovered": len(self.world.people.recovered)
                    }
            # self.log_infection_generation(day)
            # self.log_r0()
        json_path = os.path.join(self.save_path, "data.json")
        with open(json_path, "w") as f:
            json.dump(self.data_dict, f)
       

    def total_people_by_age_range(self, people):
        """
        Return dictionary of people in specified age range.

        age_ranges should be given as a list of lists, e.g. [[0, 18], [18-65], [65-99]] where the ages are inclusive.
        """
        total_people_in_age_range = {}
        all_ages = [person.age for person in people]
        for ages in self.age_ranges:
            label = "{}-{}".format(ages[0], ages[1])
            total_people_in_age_range[label] = sum([all_ages.count(i) for i in range(ages[0], ages[1]+1)])
        return total_people_in_age_range


    def total_people_per_area_by_age_range(self):
        total_people_per_area_by_age = {area.name: {} for area in self.world.areas.members}

        for area in self.world.areas.members:
            total_people_per_area_by_age[area.name] = self.total_people_by_age_range(area.people)
        
        return total_people_per_area_by_age
                

    def get_infected_people_area(self, area):
        infected = {}
        susceptible = {}
        recovered = {}
        total_people_by_area_by_age = {}
        for person in area.people:
            if person.health_information.susceptible:
                if person.age in susceptible:
                    susceptible[person.age] += 1
                else:
                    susceptible[person.age] = 1

            if person.health_information.infected:
                if person.age in infected:
                    infected[person.age] += 1
                else:
                    infected[person.age] = 1

            if person.health_information.recovered:
                if person.age in recovered:
                    recovered[person.age] += 1
                else:
                    recovered[person.age] = 1
        return susceptible, infected, recovered


    def log_r0(self):
        if self.timer.day_int+1 == self.timer.total_days: # dirty fix, need to rethink later
            inner_dict = {}
            r0s_raw = []
            r0s_recon = []
            for person in self.world.people.recovered:
                day_inf = person.health_information.time_of_infection
                if (day_inf > 1 and day_inf < 5): # need to think about how to define this better
                    day_recover = day_inf + person.health_information.length_of_infection
                    s_ti = self.data_dict["world"][day_inf]["susceptible"]
                    s_tr = self.data_dict["world"][day_recover]["susceptible"]
                    s_frac = (s_ti + s_tr) / (2 * self.world.people.total_people)
                    r0 = person.health_information.number_of_infected
                    r0s_raw.append(r0)
                    r0s_recon.append(r0 / s_frac)

                    inner_dict[person.id] = {"start" : day_inf,
                                            "length" : person.health_information.length_of_infection,
                                            "num_infected" : person.health_information.number_of_infected,
                                            "R0_raw" : r0,
                                            "R0_recon" : r0 / s_frac}
            
            self.data_dict["data"] = inner_dict
            self.data_dict["R0_raw"] = np.mean(r0s_raw)
            self.data_dict["R0_recon"] = np.mean(r0s_recon)


    def log_R(self):
        R_counter = {k: 0 for k in self.data_dict["world"].keys()}
        R_denom   = {k: 0 for k in self.data_dict["world"].keys()}
        R = {}
        for person in self.world.people.recovered:
            day_inf = person.health_information.time_of_infection
            infecter = person.health_information.infecter
            if infecter is not None:
                day_infecter_inf = infecter.health_information.time_of_infection
            
            # R denom counts the number of everyone infected on a given day
            R_denom[day_inf] += 1
            # R counter counts the number of people infected on a day that go on to infect other people
            # infectors are not unique, so it counts the number of people they infect
            R_counter[day_infecter_inf] += 1
        for day in self.data_dict["world"].keys():
            if R_denom[day] == 0 or R_counter[day] == 0:
                R[day] = 1E-10
                continue
            R[day] = R_counter[day] / R_denom[day]
        return R_counter, R_denom, R


    def plot_R(self):
        _, _, R = self.log_R()
        times = list(self.data_dict["world"].keys())
        plt.figure()
        plt.plot(times, [R[time] for time in times])
        plt.xlabel('Days')
        plt.ylabel('R(t)')
        plt.show()


    def plot_infections_per_day(self):
        days = list(self.data_dict["world"].keys())
        
        plt.figure()
        for ages in self.age_ranges:
            label = "{}-{}".format(ages[0], ages[1])
            plt.plot(days, list(self.data_dict["ByAge"][label]["infected"].values()), label=label)
        plt.xlabel("Days")
        plt.ylabel("Infections per day")
        plt.legend()
        plt.show()


    def plot_infection_location(self, return_data=False):
        locations = {}
        for person in self.world.people.recovered:
            if person.health_information.group_type_of_infection in locations:
                locations[person.health_information.group_type_of_infection] += 1
            else:
                locations[person.health_information.group_type_of_infection] = 1

        for person in self.world.people.infected:
            if person.health_information.group_type_of_infection in locations:
                locations[person.health_information.group_type_of_infection] += 1
            else:
                locations[person.health_information.group_type_of_infection] = 1

        fig = plt.figure()
        plt.bar(locations.keys(), locations.values())
        plt.title('Locations of where infections took place')
        plt.ylabel('Number of people')
        plt.show()

        if return_data == False:
            return fig
        else:
            return fig, locations


    def plot_cumulative_fraction(self, by_age=True):
        cumulative_inf = []
        days = list(self.data_dict["world"].keys())
        total_people = self.world.people.total_people
        for day in days:
            cumulative_inf.append(self.data_dict["world"][day]["cumulative_infected"])
        
        fig = plt.figure()
        if by_age == False:
            plt.plot(days, np.array(cumulative_inf) / total_people, label='total')
        else:
            total_people_by_age = self.total_people_by_age_range(self.world.people.members)
            print(total_people_by_age)
            for ages in self.age_ranges:
                label = "{}-{}".format(ages[0], ages[1])
                plt.plot(days, np.array(list(self.data_dict["ByAge"][label]["cumulative_infected"].values())) / total_people_by_age[label], label=label)
        plt.xlabel("Days")
        plt.ylabel("Cumulative fraction of population infected")
        plt.legend()
        plt.show()
        return fig


    def plot_infection_curves_per_day(self):
        infected = []
        susceptible = []
        recovered = []
        # first_area = list(self.data_dict.keys())[0]
        days = list(self.data_dict["world"].keys())
        for day in days:
            n_inf = self.data_dict["world"][day]["infected"]
            n_susc = self.data_dict["world"][day]["susceptible"]
            n_rec = self.data_dict["world"][day]["recovered"]
            infected.append(n_inf)
            susceptible.append(n_susc)
            recovered.append(n_rec)
        fig, ax = plt.subplots()
        ax.plot(days, infected, label="Infected", color='C0')
        ax.plot(days, susceptible, label="Susceptible", color='C1')
        ax.plot(days, recovered, label="Recovered", color='C2')
        ax.set_xlabel("Days")
        ax.set_ylabel("Number of people")
        ax.set_title("Infection curves")
        fig.legend()

        if self.box_mode:
            def ratio_SIR_numerical(beta, gamma, N, I_0, times):
                """
                Numerical simulation of SIR model with simple Euler stepper in 10*times timesteps, 
                output are two lists contained number of infected and recovered at each timestep
                beta  = transmission coefficient in units of 1/time
                gamma = recovery coefficient in units of 1/time
                N     = overall size of the group
                I_0   = number of initially infected people
                """
                S_list = []
                I_list = []
                R_list = []
                I = I_0
                S = N - I_0
                R = 0
                step = 10
                for time in times:
                    for i in range(step):
                        S = S - beta / step * S * I / N
                        I = I + beta / step * S * I / N - gamma / step * I
                        R = R + gamma / step * I
                    S_list.append(S)
                    I_list.append(I)
                    R_list.append(R)
                return S_list, I_list, R_list
            

            N = len(self.world.people)
            I_0 = self.data_dict["world"][list(self.data_dict["world"].keys())[0]]["infected"]

            beta = self.simulator.selector.transmission_probability
            beta /= self.timer.get_number_shifts(None) # divide by the number of timesteps we do per day, this only works if the timesteps are equal in length for now
            gamma = self.simulator.selector.recovery_rate
            gamma /= self.timer.get_number_shifts(None)
            # multiply by 2 to compensate for updating health status twice in each timestep, see interaction/base.py

            n_sus, n_inf, n_rec = ratio_SIR_numerical(beta, gamma, N, I_0, day_array)

            ax.plot(day_array, n_inf, color='C0', linestyle='--')
            ax.plot(day_array, n_sus, color='C1', linestyle='--')
            ax.plot(day_array, n_rec, color='C2', linestyle='--')

        fig.savefig(os.path.join(self.save_path, "infection_curves.png"), dpi=300)
        return fig, ax

    def plot_r0_map(self):
        pass

    def get_infection_duration(self):
        lengths = []
        predictions = []
        for person in self.world.people.members:
            if person.health_information.recovered:
                lengths.append(person.health_information.length_of_infection)
                predictions.append(person.health_information.infection.symptoms.predicted_recovery_time)
        return lengths
