class Interaction:
    def __init__(self, interaction_config):
        self.active_groups = None
        pass

    def time_step(self):
        # set everyone to the right group
        for grouptype in self.active_groups:
            for group in grouptype.members:
                if group.size() != 0:
                    group.group.update_status_lists()
        # run time step for each group
        for grouptype in self.active_groups:
            for group in grouptype.members:
                if group.size() != 0:
                    self.single_time_step_for_group(group)
        # update infection status for each group 
        # question: should we advance time here?
        for grouptype in self.active_groups:
            for group in grouptype.members:
                if group.size() != 0:
                    group.update_status_lists()
                    


