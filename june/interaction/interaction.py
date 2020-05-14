from abc import ABC, abstractmethod


class Interaction(ABC):
    def time_step(self, time, health_index_generator, delta_time, group):
        if group.contains_people:
            self.single_time_step_for_group(group, health_index_generator, time, delta_time)

    @abstractmethod
    def single_time_step_for_group(self, group, health_index_generator, time, delta_time):
        pass
