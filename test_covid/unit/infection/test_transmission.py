from covid.infection import transmission as trans

import pytest


class TestTransmission:

    def test__update_probability_at_time(self):

        transmission = trans.TransmissionConstant(proabability=0.3)

        assert transmission.probability == 0.3










