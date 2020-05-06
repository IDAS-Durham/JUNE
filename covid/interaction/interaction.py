import random
import numpy as np

class Interaction:
    def __init__(self,parameters=None):
        pass
        
    def time_step(self, time, delta_time, group):
        # TODO : Is there any reason for this to be passed all groups, as opposed to one group at a time?
        # TODO : If not, make the class assume it always acts on one group (which could have sub groups internally).

        # TODO think how we treat the double update_status_lists and make it consistent
        # with delta_time
        self.time       = time
        self.delta_time = delta_time
        self.group      = group
        if self.group.size != 0:
            self.group.update_status_lists(time=self.time, delta_time=0)
            self.single_time_step_for_group()
            self.group.update_status_lists(time=self.time, delta_time=self.delta_time)
                    
    def single_time_step_for_group(self):
        raise NotImplementedError()


