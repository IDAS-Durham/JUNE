from covid.infection import transmission as trans
from covid import time as t

import pytest


class TestTransmission:

    def test__update_probability(self):

        transmission = trans.Transmission(constant=0.3, timer=t.Timer())

        assert transmission.constant == 0.3
     #   assert transmission.update_probability()








