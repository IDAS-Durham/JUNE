"""
Class to log all important information at each timestep.
"""
import json
import os
import numpy as np
import matplotlib.pyplot as plt


class Logger:
    def __init__(self, simulator, world, timer, save_path="results"):
        self.simulator = simulator
        self.world = world
        self.timer = timer
        self.data_dict = {}
        self.save_path = save_path
        self.box_mode = self.world.box_mode
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)
        self.init_logger()

    def init_logger(self):
        if not self.box_mode:
            for area in self.world.areas.members:
                self.data_dict[area.name] = {}
        self.data_dict["world"] = {}

    def log_timestep(self, day):
        susceptible_world = 0
        infected_world = 0
        recovered_world = 0
        if not self.box_mode:
            for area in self.world.areas.members:
                susceptible, infected, recovered = self.get_infected_people_area(area)
                susceptible_world += susceptible
                infected_world += infected
                recovered_world += recovered
                self.data_dict[area.name][day] = {
                        "susceptible": susceptible,
                        "infected": infected,
                        "recovered": recovered,
                        }

            self.data_dict["world"][day] = {
                    "susceptible": susceptible_world,
                    "infected": infected_world,
                    "recovered": recovered_world,
                    }
            #self.log_r0() TODO implement
        else:
            box = self.world.boxes.members[0]
            self.data_dict["world"][day] = {
                    "susceptible": len(self.world.people.susceptible),
                    "infected": len(self.world.people.infected),
                    "recovered": len(self.world.people.recovered)
                    }
            # self.log_infection_generation(day)
            #self.log_r0()
        json_path = os.path.join(self.save_path, "data.json")
        with open(json_path, "w") as f:
            json.dump(self.data_dict, f)

    def get_infected_people_area(self, area):
        infected = 0
        susceptible = 0
        recovered = 0
        for person in area.people:
            if person.health_information.susceptible:
                susceptible += 1
            if person.health_information.infected:
                infected += 1
            if person.health_information.recovered:
                recovered += 1
        return susceptible, infected, recovered


    def log_infection_generation(self, day):
        infection_generation_global = 0
        global_counter = 0
        if not self.box_mode:
            for area in self.world.areas.members:
                for person in area.people:
                    if person.health_information.infected:
                        infection_generation_global += person.health_information.infection_generation
                        global_counter +=1
                        
            if infection_generation_global == 0:
                self.data_dict["world"][day]["infection_generation"] = 0
            else:
                self.data_dict["world"][day]["infection_generation"] = infection_generation_global / global_counter
        else:
            box = self.world.boxes.members[0]
            for person in box.people:
                infection_generation_global += person.health_information.infection_generation
                global_counter += 1
                
                self.data_dict["world"][day]["infection_generation"] = infection_generation_global / global_counter


    def log_r0(self):
        if not self.box_mode:
            raise NotImplementedError()
        else:
            box = self.world.boxes.members[0]
            if self.timer.day_int+1 == self.timer.total_days: # dirty fix, need to rethink later
                inner_dict = {}
                r0s_raw = []
                r0s_recon = []
                day_infs = []
                for person in box.recovered:
                    day_inf = person.health_information.time_of_infection
                    day_infs.append([day_inf, person])
                    if (day_inf > 1 and day_inf < 5): # need to think about how to define this better
                        day_recover = day_inf + person.health_information.length_of_infection
                        s_ti = self.data_dict["world"][day_inf]["susceptible"]
                        s_tr = self.data_dict["world"][day_recover]["susceptible"]
                        s_frac = (s_ti + s_tr) / (2 * len(box.people))
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


    def plot_infection_generation(self):
        import matplotlib.pyplot as plt
        days = []
        infection_generations = []
        for day in self.data_dict["world"].keys():
            days.append(day)
            infection_generations.append(self.data_dict["world"][day]["infection_generation"])
        idx_sorted = np.argsort(days)
        days = np.array(days)[idx_sorted]
        infection_generations = np.array(infection_generations)[idx_sorted]
        fig, ax = plt.subplots()
        ax.plot(days, infection_generations)
        ax.set_xlabel("Days")
        ax.set_ylabel("Average infection generation")
        return fig, ax
    

    def log_r_effective(self, day):
        """
        Computes effective R per day from individual data.
        """
        r0_global = 0
        global_counter = 0
        if not self.box_mode:
            for area in self.world.areas.members:
                r0_area = 0
                area_counter = 0
                for person in area.people:
                    if person.health_information.infected == True:
                        r0_area += person.health_information.number_of_infected
                        r0_global += person.health_information.number_of_infected
                        area_counter += 1
                        global_counter += 1
                if area_counter == 0:
                    self.data_dict[area.name][day]["r0"] = 0
                else:
                    self.data_dict[area.name][day]["r0"] = r0_area / area_counter
            if global_counter == 0: 
                self.data_dict["world"][day]["r0"] = 0
            else:
                self.data_dict["world"][day]["r0"] = r0_global / global_counter



    def plot_r_eff(self):
        import matplotlib.pyplot as plt
        days = []
        r_effs = []
        for day in self.data_dict["world"].keys():
            if np.isclose(day, int(day)):
                days.append(day)
                r_effs.append(self.data_dict["world"][day]["R_eff"])
        idx_sorted = np.argsort(days)
        days = np.array(days)[idx_sorted]
        r_effs = np.array(r_effs)[idx_sorted]
        fig, ax = plt.subplots()
        ax.plot(days, r_effs)
        ax.set_xlabel("Days")
        ax.set_ylabel("R_eff")
        return fig, ax


    def plot_infection_curves_per_day(self):
        infected = []
        susceptible = []
        recovered = []
        day_array = []
        first_area = list(self.data_dict.keys())[0]
        days = self.data_dict["world"].keys()
        for day in days:
            day_array.append(day)
            n_inf = self.data_dict["world"][day]["infected"]
            n_susc = self.data_dict["world"][day]["susceptible"]
            n_rec = self.data_dict["world"][day]["recovered"]
            infected.append(n_inf)
            susceptible.append(n_susc)
            recovered.append(n_rec)
        fig, ax = plt.subplots()
        ax.plot(day_array, infected, label="Infected", color='C0')
        ax.plot(day_array, susceptible, label="Susceptible", color='C1')
        ax.plot(day_array, recovered, label="Recovered", color='C2')
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









