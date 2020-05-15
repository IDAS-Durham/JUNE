from june.groups.group import Group, Supergroup
from typing import List
from june.demography import Population


class Box(Group):
    def __init__(self):
        super().__init__()
    
    def set_population(self, population: Population):
        self[super().GroupType.default]._people.update(population)

class Boxes(Supergroup):
    def __init__(self, boxes: List[Box]):
        super().__init__()
        self.members = boxes

    def erase_people_from_groups_and_subgroups(self):
        pass
