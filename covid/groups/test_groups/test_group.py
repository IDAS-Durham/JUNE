from covid.groups import Group
from covid.groups import Person
from scipy import stats
import numpy as np


class TestGroup(Group):
    def __init__(self, number):
        super().__init__("testgroup_%05d" % number, "TestGroup")
        self.people = []


class TestGroups:
    def __init__(self, people_per_group=5000, total_people=100000):
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
        sex_random = np.random.randint(0, 1, group_size)
        age_random = np.random.randint(0, 16, group_size)

        for i in range(0, group_size):
            person = Person(i, None, age_random[i], sex_random[i], 0, 0)
            group.people.append(person)

    def set_active_members(self):
        for group in self.members:
            for person in group.people:
                if person.active_group == None:
                    person.active_group = "testgroup"

