from june.groups import Supergroup
from june.groups import Group
from june.demography import Person
from enum import IntEnum
import numpy as np
import pytest


class MockSupergroup(Supergroup):
    def __init__(self, groups):
        super().__init__(groups)


class MockGroup(Group):
    class SubgroupType(IntEnum):
        type1 = 0
        type2 = 0

    def __init__(self):
        super().__init__()
        person = Person()
        self.add(Person(), "primary_activity", self.SubgroupType.type1)
        person = Person()
        self.add(person, "primary_activity", self.SubgroupType.type2)


@pytest.fixture(name="super_group", scope="module")
def make_supergroup():
    groups_list = [MockGroup() for _ in range(10)]
    super_group = MockSupergroup(groups_list)
    return super_group


def test__create_supergroup(super_group):
    assert len(super_group) == 10
    assert super_group.group_type == "MockSupergroup"
    return super_group
