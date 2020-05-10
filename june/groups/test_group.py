import numpy as np
from scipy import stats

from june.groups.group import Group
from june.demography.person import Person
from enum import IntEnum


class TestGroup(Group):
    def __init__(self, number):
        super().__init__(f"test_{number}", "TestGroup")

    class GroupType(IntEnum):
        default = 0

    def add(self, person, qualifier):
        super().add(person, qualifier)


class TestGroups:
    def __init__(self, people_per_group=100000, total_people=100000,config=None):
        self.members = []
        self.total_people = total_people
        self.people_per_group = people_per_group
        self.initialize_test_groups()

    def initialize_test_groups(self):
        no_people = self.total_people
        if no_people % self.people_per_group == 0:
            no_of_groups = no_people // self.people_per_group
            lastgroupsize = self.people_per_group
        else:
            no_of_groups = no_people // self.people_per_group + 1
            lastgroupsize = no_people % self.people_per_group
            
        for i in range(0, no_of_groups-1):
            group = TestGroup(i)
            self.fill_group_with_random_people(group, self.people_per_group)
            self.members.append(group)
        # last group
        group = TestGroup(no_of_groups-1)
        self.fill_group_with_random_people(group, lastgroupsize)
        self.members.append(group)

    def fill_group_with_random_people(self, group, group_size):
        sex_random = np.random.randint(0, 2, group_size)
        age_random = np.random.randint(0, 80, group_size)

        for i in range(0, group_size):
            person = Person(i, None, age_random[i], 0, sex_random[i],  0)
            group.people.append(person)

    def set_active_members(self):
        for group in self.members:
            for person in group.people:
                if person.active_group == None:
                    person.active_group = "testgroup"

