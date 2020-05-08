import pytest

from june import exc
from june.groups import group as g, Person


class TestGroup:

    def test__sanity_check_of_allowed_group(self):
        g.Group(name="house1", spec="household")

        with pytest.raises(exc.GroupException):
            g.Group(name="house1", spec="invalid")

    def test_group_types(self):
        group = g.Group(
            name="name",
            spec="household"
        )
        group.add(
            Person()
        )
        assert group[g.Group.GroupType.default].size == 1
