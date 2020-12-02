from june.groups import Group, Supergroup
from typing import List
from june.demography import Population


class Box(Group):
    def __init__(self):
        super().__init__()
        self.contact_matrices = {}
    
    def set_population(self, population: Population):
        subgroup = self[self.SubgroupType.default]
        for person in population:
            subgroup.append(person)
            person.subgroups.box = subgroup

class Boxes(Supergroup):
    def __init__(self, boxes: List[Box]):
        super().__init__(boxes)

    def erase_people_from_groups_and_subgroups(self):
        pass
