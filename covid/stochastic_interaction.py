from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


class StochasticInteraction(Interaction):
    def init(self):
        self.fill_defaults()
                
    def single_time_step_for_group(self, group):
        self.group = group
        if (self.group.size() <= 1 or
            self.group.size_infected() == 0 or
            self.group.size_susceptible() == 0):
            return
        transmission_probability = self.calculate_transmission_probability()
        if (transmission_probability>0.001): 
            for recipient in self.group.get_susceptible():
                self.single_time_step_for_recipient(recipient, transmission_probability)

    def calculate_transmission_probability(self):
        spec = self.group.get_spec() 
        if spec=="Household" or spec=="TestGroup":
            return self.calculate_localised_transmission_probability()
        elif spec=="School":
            return self.calculate_localised_transmisson_probability()
        elif spec=="Work_Outdoor" or spec=="Work_Indoor":
            return self.calculate_localised_transmission_probability()
        else:
            return 0.

    def calculate_localised_transmission_probability(self):
        intensity      = self.group.get_intensity(self.time)
        if self.group.get_spec()=="household":
            intensity /= self.group.get_size()**self.alpha
        summed_prob  = 0.
        self.weights = []
        for person in self.group.get_infected():
            probability  = person.transmission_probability(self.time)
            probability *= self.severity_multiplier(self.group.get_spec())
            summed_prob += probability
            self.weights.append([person,probability])
        for i in len(self.weights):
            self.weights[i][1] /= summed_prob
        return intensity * summed_prob * self.delta_t

    def single_time_step_for_recipient(self,recipient,transmission_probability):
        recipient_probability = recipient.get_susceptibility()
        if recipient_probability > 0.0:
            if random.random() <= 1.-np.exp(-transmission_probability * recipient_probability):
                recipient.set_infection(
                    self.selector.make_infection(recipient, self.time)
                )
                recipient.get_counter().update_infection_data(self.time,self.group.get_spec())
                disc = random.random()
                i    = 0
                while disc>0. and i<len(self.weights)-1:
                    i += 1
                self.weights[i][0].get_counter().increment_infected()
                
    def fill_defaults(self):
        # infection modifiers for non-asymptomatic cases
        self.severe = "constant"
        self.omega  = 2
        # I have added another psi factor - this make households and
        # school/workplace nearly identical
        self.psi    = []
        self.psi.append(0.0)  
        self.psi.append(0.1)  
        self.psi.append(0.2)
        self.psi.append(0.25)
        self.psi.append(0.5)
        
        # transmission strength for different groups:
        # this should be made a group parameter (intensity)
        #self.beta_h = 0.47        # households
        #self.beta_p = []          # strength at different places
        #self.beta_p.append(0.94)  # school type 1
        #self.beta_p.append(0.94)  # school type 2
        #self.beta_p.append(0.94)  # school type 3
        #self.beta_p.append(0.47)  # school type 4
        #self.beta_c = 0.0  # community
        # scaling exponent for household size
        #self.alpha  = 0.8
        # modifiers for non-asymptomatic cases at 4 different
        # types of place: 1-3 = schools, 4 = workplace
