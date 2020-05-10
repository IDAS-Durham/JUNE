import random
from abc import ABC, abstractmethod

import numpy as np

class Interaction(ABC):
        
    def time_step(self, time, delta_time, group):
       if group.contains_people:
            self.single_time_step_for_group(group, time, delta_time)
                    
    @abstractmethod
    def single_time_step_for_group(self):
        pass

