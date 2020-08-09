from typing import List
import collections
from june.groups import Group, Supergroup
from june.demography import Person


class LearningCenter(Group):
    def __init__(self):
        super().__init__()
        self.active_shift = 0
        self.has_shifts = True
        self.ids_per_shift = collections.defaultdict(list)
    
    def add(self, person: Person, shift: int):
        super().add(person=person, activity="primary_activity", subgroup_type=0)
        self.ids_per_shift[shift].append(person.id)

class LearningCenters(Supergroup):
    def __init__(self, learning_centers: List[LearningCenter]):
        super().__init__()
        self.members = learning_centers 
        self.has_shifts = True

    def get_closest(self):
        return self[0]
    
    def activate_next_shift(self, n_shifts):
        for learning_center in self.members:
            learning_center.active_shift += 1
            if learning_center.active_shift == n_shifts:
                learning_center.active_shift = 0



