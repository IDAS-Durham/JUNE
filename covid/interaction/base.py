from covid.interaction.parameters import ParameterInitializer
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random

class Interaction(ParameterInitializer):

    def __init__(self, user_parameters, required_parameters, world):
        super().__init__("interaction", user_parameters, required_parameters)
        self.groups       = []
        self.world       = world
        self.intensities = {}

    def time_step(self):
        #print ("start time_step for ",len(self.groups)," groups")
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size != 0:
                    group.update_status_lists()
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size != 0:
                    self.single_time_step_for_group(group)
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size != 0:
                    group.update_status_lists()
        #print ("end time_step for ",len(self.groups)," groups")

    def single_time_step_for_group(self, group):
        pass

    def get_intensity(self,grouptype):
        if grouptype in self.intensities:
            return self.intensities[grouptype]
        return 1

    def set_intensities(self,intensities):
        self.intensities = intensities

    def set_intensity(self,grouptype,intensity):
        self.intensities[grouptype] = intensity
        




