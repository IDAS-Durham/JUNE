from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


class StochasticInteraction(Interaction):
    self.allowed_severe_tags = ["none", "constant", "differential"]

    def init(self):
        self.fill_defaults()
        if "severe_treatment" in self.params["parameters"]:
            self.severe = self.params["parameters"]["severe_treatment"]
            if not (self.severe in allowed_severe_tags):
                self.severe = "constant"
        ### in the IC model this is a constant
        if "omega" in self.params["parameters"]:
            self.omega  = self.params["parameters"]["omega"]

                
    def single_time_step_for_group(self, group):
        if (group.size() <= 1 or
            group.size_infected() == 0 or
            group.size_susceptible() == 0):
            return
        transmission_probability = self.calculate_transmission_probability(group)
        if (transmission_probability>0.001): 
            for recipient in group.get_susceptible():
                self.single_time_step_for_recipient(recipient, transmission_probability)

    def calculate_transmission_probability(self,group):
        spec = group.get_spec() 
        if spec=="Household" or spec=="TestGroup":
            return self.calculate_localised_transmission_probability(group)
        elif spec=="School":
            psitag = 0
            return self.calculate_localised_transmisson_probability(group,psitag)
        elif spec=="Work:Outdoor" or spec=="Work:Indoor":
            psitag = 3
            return self.calculate_localised_transmission_probability(group,psitag)
        else:
            return 0.

    def calculate_localised_transmission_probability(self,group,psitag):
        intensity      = group.get_intensity(self.time)
        if psitag==0:
            intensity /= group.get_size()**self.alpha
        summed_prob = 0.
        for person in group.get_infected():
            probability = person.transmission_probability(self.time)
            if self.severe=="constant":
                tag = person.get_symptons_tag()
                if (tag=="influenza-like illness" or tag=="pneumonia" or
                    tag=="hospitalised" or tag=="intensive care"):
                    probability *= (self.omega * self.psi[psitag] - 1.)
            elif self.severe=="differential":
                probability *= (1.+self.omega*person.get_severity(self.time))
            summed_prob += probability
        return intensity * summed_prob * self.delta_t

    def single_time_step_for_recipient(self,recipient,transmission_probability):
        recipient_probability = recipient.get_susceptibility()
        if recipient_probability > 0.0:
            if random.random() <= np.exp(-transmission_probability * recipient_probability):
                recipient.set_infection(
                    self.selector.make_infection(recipient, self.time)
                )
                
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
