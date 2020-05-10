from june.infection import transmission as trans

import autofit as af
import os
import pytest

directory = os.path.dirname(os.path.realpath(__file__))

@pytest.fixture(scope="session", autouse=True)
def do_something():
    af.conf.instance = af.conf.Config(config_path="{}/files/config/".format(directory))

class TestTransmission:

    def test__update_probability_at_time(self):

        transmission = trans.TransmissionConstant(probability=0.3)

        assert transmission.probability == 0.3

    def test__object_from_config(self):

        transission = trans.Transmission.object_from_config()

        assert transission == trans.TransmissionConstant








