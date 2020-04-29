from covid.infection import transmission as trans
from covid import time as t

import pytest


class TestTransmission:

    def test__update_probability_at_time(self):

        transmission = trans.TransmissionConstant(start_time=0.0, proabability=0.3)

        assert transmission.start_time == 0.0
        assert transmission.probability == 0.3

        transmission.update_probability_at_time(time=0.5)

        assert transmission.last_time_updated == 0.5









