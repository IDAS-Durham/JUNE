from june.groups import Supergroup
from june.groups import Group
from june.demography import Person
from enum import IntEnum
import numpy as np
import pytest


class MockSupergroup(Supergroup):
    def __init__(self, groups):
        references_to_people = ["a", "b"]
        super().__init__(references_to_people)
        self.members = groups



class MockGroup(Group):
    class SubgroupType(IntEnum):
        type1 = 0
        type2 = 0

    def __init__(self):
        super().__init__()
        self.a = np.random.randint(1, 10)
        self.b = np.random.randint(1, 10)
        self.c = np.random.randint(1, 10)
        self.d = np.random.randint(1, 10)
        person = Person()
        self.add(Person(), person.ActivityType.box, self.SubgroupType.type1)
        person = Person()
        self.add(person, person.ActivityType.box, self.SubgroupType.type2)

@pytest.fixture(name="super_group", scope="module")
def make_supergroup():
    groups_list = [MockGroup() for _ in range(10)]
    super_group = MockSupergroup(groups_list)
    return super_group

def test__create_supergroup(super_group):
    assert len(super_group) == 10
    assert super_group.group_type == "MockSupergroup"
    return super_group

def test__erase_all_groups_information(super_group):
    super_group.erase_people_from_groups_and_subgroups()
    for group in super_group:
        assert group.c is not None
        assert group.d is not None
        assert group.a is None
        assert group.b is None
        for subgroup in group.subgroups:
            for slot in subgroup.__slots__:
                assert len(getattr(subgroup, slot)) == 0
