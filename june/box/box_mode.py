from june.groups.group import Group
from typing import List
from june.demography import Population


class Box(Group):
    def __init__(self):
        super().__init__()
    
    def set_population(self, population: Population):
        for person in population.people:
            self.people.add(person)


class Boxes:
    def __init__(self, boxes: List[Box]):
        self.members = boxes


