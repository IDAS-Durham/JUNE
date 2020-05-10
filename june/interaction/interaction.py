import random
from abc import ABC, abstractmethod

import numpy as np

class Interaction(ABC):
        
    def time_step(self, time, health_index_generator, delta_time, group):
       if group.size != 0:
            self.single_time_step_for_group(group, health_index_generator,time, delta_time)
                    
    @abstractmethod
    def single_time_step_for_group(self):
        pass

