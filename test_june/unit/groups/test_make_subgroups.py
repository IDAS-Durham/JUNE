from june.groups import Supergroup
from june.groups import Group
from june.demography import Person
from enum import IntEnum
import pytest
from june import paths
import itertools


from june.groups.group import make_subgroups

interaction_config = (
    paths.configs_path / "tests/groups/make_subgroups_test_interaction.yaml"
)


class MockGroup(Group):
    def __init__(self):
        super().__init__()


class MockSupergroup(Supergroup):
    venue_class = MockGroup

    def __init__(self, groups):
        super().__init__(groups)


@pytest.fixture(name="super_group_default", scope="module")
def make_supergroup_default():
    MockSupergroup.Get_Interaction(interaction_config)
    groups_list = [MockSupergroup.venue_class() for _ in range(10)]
    super_group_default = MockSupergroup(groups_list)
    return super_group_default


@pytest.fixture(name="super_group", scope="module")
def make_supergroup():
    MockSupergroup.Get_Interaction(interaction_config)
    groups_list = [MockSupergroup.venue_class() for _ in range(10)]
    super_group = MockSupergroup(groups_list)
    return super_group


def test__make_subgroups_defualt(super_group_default):
    assert super_group_default[0].subgroup_type == "Age"
    assert super_group_default[0].subgroup_bins == [0, 18, 60, 100]
    assert super_group_default[0].subgroup_labels == ["A", "B", "C"]


def test__make_subgroups(super_group):
    assert super_group[0].subgroup_type == "Age"
    assert super_group[0].subgroup_bins == [0, 18, 60, 100]
    assert super_group[0].subgroup_labels == ["A", "B", "C"]


def test_excel_cols():
    assert list(
        itertools.islice(make_subgroups.Subgroup_Params().excel_cols(), 10)
    ) == ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
