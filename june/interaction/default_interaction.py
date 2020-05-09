import random
import numpy as np
import yaml
import sys
from pathlib import Path
from interaction.interaction import Interaction
from groups.group.group import Group

default_config_filename = (
    Path(__file__).parent.parent.parent
    / "configs/defaults/interaction/DefaultInteraction.yaml"
)

class DefaultInteraction(Interaction):

    def __init__(self, parameters):
        self.contacts = {}
        self.physical = {}
        self.beta     = {}
        self.alpha    = parameters["alpha_physical"]
        self.schoolC  = 2.50
        self.schoolP  = 0.15
        self.schoolxi = 0.30
        for tag in Group.allowed_groups:
            self.fix_group_matrices(tag,parameters)

    def fix_group_matrices(self,tag,parameters):
        self.beta[tag]     = 1.
        self.contacts[tag] = [[1.]]
        self.physical[tag] = [[0.]]
        if tag in parameters:
            if "beta" in parameters[tag]:
                self.beta[tag]     = parameters[tag]["beta"]
            if "contacts" in parameters[tag]:
                self.contacts[tag] = parameters[tag]["contacts"]
            if "physical" in parameters[tag]:
                self.physical[tag] = parameters[tag]["physical"]
        if tag=="school":
            if "xi" in parameters[tag]:
                self.schoolxi = float(parameters[tag]["xi"])
            if (len(self.contacts["school"])==2 and
                len(self.physical["school"])==2):
                self.schoolC = float(self.contacts["school"][1][1])
                self.schoolP = float(self.physical["school"][1][1])
        

    @classmethod
    def from_file(
            cls, config_filename: str  = default_config_filename
    ) -> "DefaultInteraction":

        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        return DefaultInteraction(config['parameters'])
   
    def single_time_step_for_group(self, group, time, delta_time):
        """
        Runs the interaction model for a time step
        Parameters
        ----------
        group:
            group to run the interaction on
        time:
            time at which the interaction starts to take place
        delta_time: 
            duration of the interaction 
        """
        self.probabilities = []
        self.weights = []

        #if group.must_timestep:
        self.calculate_probabilities(group)
        n_subgroups = len(group.subgroups)
        for i in range(n_subgroups):
            for j in range(n_subgroups):
                # grouping[i] infected infects grouping[j] susceptible
                self.contaminate(group, time, delta_time, i,j)
                if i!=j:
                    # =grouping[j] infected infects grouping[i] susceptible
                    self.contaminate(group, time, delta_time, j,i)

    def contaminate(self, group, time, delta_time,  infecters,recipients):
        #TODO: subtitute by matrices read from file when ready
        n_subgroups = len(group.subgroups)
        contact_matrix = np.ones((n_subgroups, n_subgroups))
        if (
            contact_matrix[infecters][recipients] <= 0. or
            self.probabilities[infecters] <= 0.
        ):
            return
        for recipient in group.subgroups[recipients]:
            transmission_probability = 1.0 - np.exp(
                -delta_time *
                recipient.health_information.susceptibility *
                self.intensity(group,infecters,recipients) *
                self.probabilities[infecters]
            )
            if random.random() <= transmission_probability:
                infecter = self.select_infecter()
                infecter.health_information.infection.infect_person_at_time(
                    person=recipient, time=time
                )
                infecter.health_information.increment_infected()
                recipient.health_information.update_infection_data(
                    time=time, group_type=group.spec
                )

    def intensity(self,group,infecter,recipient):
        tag = group.spec
        if tag=="school":
            if infecter>0 and recipient>0:
                delta = pow(self.schoolxi,abs(recipient-infecter))
                mixer = self.schoolC * delta
                phys  = self.schoolP * delta
            elif infecter==0 and recipient>0:
                mixer = self.contacts[tag][1][0]
                phys  = self.physical[tag][1][0]
            elif infecter>0 and recipient==0:
                mixer = self.contacts[tag][0][1]
                phys  = self.physical[tag][0][1]
            else:
                mixer = self.contacts[tag][0][0]
                phys  = self.physical[tag][0][0]
        else:
            if (recipient >= len(self.contacts[tag]) or
                infecter  >= len(self.contacts[tag][recipient])):
                mixer = 1.
                phys  = 0.
            else:
                mixer = self.contacts[tag][recipient][infecter]
                phys  = self.physical[tag][recipient][infecter]
        if tag=="commute_Public":
            # get the location-dependent group modifiers here,
            # they will take into account intensity and physicality
            # of the interaction by modifying mixer and phys.
            mixer *= 1. 
            phys  *= 1.
        return self.beta[tag] * float(mixer) * (1. + (self.alpha-1.)*float(phys))
        
    def calculate_probabilities(self, group):
        norm   = 1./max(1, group.size)
        for grouping in group.subgroups:
            summed = 0.
            for person in grouping.infected:
                individual = (
                    person.health_information.infection.transmission.probability
                )
                summed += individual*norm
                self.weights.append([person, individual])
            self.probabilities.append(summed)

    def select_infecter(self):
        """
        Assign responsiblity to infecter for infecting someone
        """
        summed_weight = 0.
        for weight in self.weights:
            summed_weight += weight[1]
        choice_weights = [w[1]/summed_weight for w in self.weights]
        idx = np.random.choice(range(len(self.weights)), 1, p=choice_weights)[0]
        return self.weights[idx][0]
