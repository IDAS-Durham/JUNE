import numpy as np
import random


class Transmission:

    def __init__(self, timer, constant=0.3):

        self.constant = constant

        self.timer = timer

        if timer != None:
            self.infection_start_time = self.timer.now
            self.last_time_updated = self.timer.now  # for testing

        self.probability = 0.0

    def update_probability(self):

        time = self.timer.now
        self.last_time_updated = time