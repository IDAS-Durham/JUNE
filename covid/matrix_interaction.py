from covid.interaction import Interaction
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random


"""
We assume that the matrices are symmetric, with age indexing rows and
columns, and that they are organised in a dictionary with the grouptype
as key.  The sum over a row then gives th total number of interactions
a person of a given age has per day in this group (we can vary this
number on a daily base with a Poissonian distribution) - if we call 
each group only once per day, this translates immediately into contacts 
per call.  The resulting number of interactions is then distributed 
over group members according to the frequency in the matrix.
"""

class MatrixInteraction(Interaction):
    def init(self):
        self.matrices = self.params["matrices"]
        self.variation_type = None
        self.check_type     = None
        if "variaton" in self.params:
            if "type" in self.params["variation"]:
            self.variation_type = self.params["variation"]["type"]
            if (self.variation_type!="Poisson"):
                self.variation_type = "Poisson"            
        if check in self.params:
            self.check_type = self.params["check"]
        if check_type = "matrix_test":
            self.testmatrices = {}
            for key in self.matrices:
                self.testmatrices[key] = self.make_empty_matrix(100)
            
            
    def single_time_step_for_group(self, group):
        if (group.size() <= 1 or
            group.size_infected() == 0 or
            group.size_susceptible() == 0):
            return
        self.matrix = self.matrices[group.get_spec()]
        people      = group.get_infected()
        if check_type = "matrix_test":
            self.test_matrix = self.test_matrices[group.get_spec()]
            people = group.get_people():
        for infecter in people:
            transmission_probability = self.calculate_single_transmission_probability(infecter) 
            Naverage  = self.calculate_average_Ncontacts(infecter)
            Ncontacts = self.calculate_actual_Ncontacts(Naverage)
            for i in range(Ncontacts):
                recipient = self.make_single_contact(infecter,group)
                if check_type = "matrix_test":
                    test_matrix[infecter.get_age()][recipient.get_age()] += 1
                    test_matrix[recipient.get_age()][infecter.get_age()] += 1
                if (not(recipient.is_infected()) and
                    recipient.susceptibility>0.):
                    if random.random() <= 1.-np.exp(-transmission_probability *
                                                    recipient.susceptibility()):
                        recipient.set_infection(
                            self.selector.make_infection(recipient, self.time)
                        )

    def make_single_contact(self,infecter,group):
        recipient = infecter
        while recipient==infecter:
            disc      = random.random()
            index     = 0
            while disc>=0. and index<len(self.options)-1:
                disc  -= self.options[index][1]
                index += 1
            recipient  = self.options[index][0]
        return recipient

    def calculate_single_transmission_probability(self,infecter):
        intensity   = group.get_intensity(self.time)
        probability = infecter.transmission_probability(self.time)
        if self.severe=="constant":
            tag = person.get_symptons_tag()
            if (tag=="influenza-like illness" or tag=="pneumonia" or
                tag=="hospitalised" or tag=="intensive care"):
                probability *= (self.omega * self.psi[psitag] - 1.)
        elif self.severe=="differential":
            probability *= (1.+self.omega*person.get_severity(self.time))
        return probability * intensity * self.delta_t
    
    def calculate_average_Ncontacts(self,infecter):
        age = max(infecter.get_age(),99)
        sum = 0.
        for j in self.matrix[age]:
            sum += self.matrix[age][j]
        self.options = []
        norm = 0.
        for partner in group.people():
            if partner!=infecter:
                entry = self.matrix[age][partner.get_age()]
                norm += entry
                self.options.append([partner,entry])
            for pair in options:
                pair[1] /= norm
        return sum

    def calculate_actual_Ncontacts(self,Nave):
        if self.variation_type=="Poisson":
            N = np.random.poisson(Nave)
        Nint  = int(N)
        Nover = N-Nint
        if np.random.random<Nover:
            Nint += 1
        return Nint

    def make_empty_matrix(self,N):
        matrix = []
        for i in range(N):
            row = []
            for j in range(N):
                row.append(0.)
            matrix.append(row)
        return matrix
