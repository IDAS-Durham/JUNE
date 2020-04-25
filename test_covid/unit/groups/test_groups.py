import pytest
import os

from covid.groups import group as g
from covid import exc

class TestGroup:

    def test__sanity_check_of_allowed_group(self):

        g.Group(name="house1", spec="household")

        with pytest.raises(exc.GroupException):
            g.Group(name="house1", spec="invalid")

    def test__intensity_can_be_set(self):

        group = g.Group(name="house1", spec="household")

        assert group.intensity == 1.0

        group.intensity = 2.0

        assert group.intensity == 2.0