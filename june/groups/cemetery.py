from june.groups.group import Group, Supergroup
from june.logger_creation import logger
from enum import IntEnum


class Cemetery:
    def __init__(self):
        self.people = []

    def add(self, person):
        self.people.append(person)


class Cemeteries(Supergroup):
    def __init__(self):
        super().__init__()
        self.members = [Cemetery()]

    def get_nearest(self, person):
        return self.members[0]
