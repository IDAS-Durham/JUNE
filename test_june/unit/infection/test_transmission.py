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





class TestTransmissionGamma:

    def test__update_probability_at_time(self):
        max_infectiousness = 4.
        shift = 3.
        shape = 3.
        rate = 2.
        transmission = trans.TransmissionGamma(
               max_infectiousness = max_infectiousness, 
               shape = shape,
               rate=rate,
               shift=shift
            )
        transmission.update_probability_from_delta_time((shape-1)/rate + shift)
        assert transmission.probability == pytest.approx(max_infectiousness,
                rel=0.01)
                
