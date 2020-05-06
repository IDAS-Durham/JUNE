import random
import numpy as np

class Interaction:
        
    def time_step(self, time, delta_time, group):
       if self.group.size != 0:
            self.single_time_step_for_group(group, time, delta_time)
            self.group.update_status_lists(time=time, delta_time=delta_time)
                    
    def single_time_step_for_group(self):
        raise NotImplementedError()


