import numpy as np
import random
import sys
from covid.interaction import Interaction
from covid.collective_interaction import CollectiveInteraction
from covid.stochastic_interaction import StochasticInteraction

class InteractionSelector:
    def __init__(self, config):
        self.itype = "collective"
        self.mode  = "probabilistic"
        if "type" in config: 
            self.itype = config["type"]
        if "mode" in config: 
            self.mode = config["mode"]

    def get(self, infection_selector, config):
        if self.itype == "collective":
            return CollectiveInteraction(infection_selector, config)
        elif self.itype == "stochastic":
            return CollectiveInteraction(infection_selector, config)
        elif self.itype == "mixing_matrix":
            print ("Interaction model ",itype," not fully implemented yet.")
            return CollectiveInteraction(infection_selector, config)
        print ("Interaction model ",itype," not implemented.  Finish the run.")
        sys.exit(1)
