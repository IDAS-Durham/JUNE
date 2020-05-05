import pytest

from covid import exc
from covid.groups import group as g, Person


class TestGroup:

    def test__sanity_check_of_allowed_group(self):
        g.Group(name="house1", spec="household")

        with pytest.raises(exc.GroupException):
            g.Group(name="house1", spec="invalid")

    def test__intensity_can_be_set(self):
        group = g.Group(name="house1", spec="household")

        assert group["default"].intensity == 1.0

        group["default"].intensity = 2.0

        assert group["default"].intensity == 2.0

    def test_group_types(self):
        group = g.Group(
            name="name",
            spec="household"
        )
        group.add(
            Person()
        )
        assert group[g.GroupType.default].size == 1
