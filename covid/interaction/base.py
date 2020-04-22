from covid.parameters import ParameterInitializer
from covid.infection import Infection
from covid.groups import Group
import numpy as np
import sys
import random

class Interaction(ParameterInitializer):

    def __init__(self, user_parameters, required_parameters, world):
        super().__init__("interaction", user_parameters, required_parameters)
        self.groups   = []
        self.world = world

    def time_step(self):
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

    def single_time_step_for_group(self, group):
        pass







