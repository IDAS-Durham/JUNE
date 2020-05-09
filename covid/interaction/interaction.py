import random
from abc import ABC, abstractmethod

import numpy as np

class Interaction(ABC):
        
    def time_step(self, time, delta_time, group):
       if group.size != 0:
            self.single_time_step_for_group(group, time, delta_time)
            #group.update_status_lists(time=time, delta_time=delta_time)
                    
    @abstractmethod
    def single_time_step_for_group(self):
        pass

