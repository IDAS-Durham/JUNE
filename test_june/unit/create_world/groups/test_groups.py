import pytest

from june.groups import group as g
from june import exc

class TestGroup:

    def test__sanity_check_of_allowed_group(self):
        g.Group(name="house1", spec="household")

        with pytest.raises(exc.GroupException):
            g.Group(name="house1", spec="invalid")

    def test__intensity_can_be_set(self):
        group = g.Group(name="house1", spec="household")

        assert group[0].intensity == 1.0

        group[0].intensity = 2.0

        assert group[0].intensity == 2.0

    def test_group_types(self):
        group = g.Group(
            name="name",
            spec="household"
        )
        group.add(
            Person()
        )
        assert group[g.Group.GroupType.default].size == 1
