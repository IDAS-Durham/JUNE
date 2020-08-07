from june.infection import transmission as trans 
import scipy.stats
import numpy as np
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

    @pytest.mark.parametrize("x", [0.,1,3,5])
    @pytest.mark.parametrize("a", [1,3,5])
    @pytest.mark.parametrize("loc", [0,-3,3])
    @pytest.mark.parametrize("scale", [1,3,5])
    def test__gamma_pdf_implementation(self, x, a, loc, scale):
        scipy_gamma = scipy.stats.gamma(a=a, loc=loc, scale=scale)
        assert  trans.gamma_pdf(x, a=a, loc=loc, scale=scale) == pytest.approx(scipy_gamma.pdf(x), rel=0.001)

    def test__gamma_pdf_vectorized(self,): 
        x = np.linspace(0.,10.,100)
        a = 1.
        loc = 1.
        scale = 1.
        scipy_gamma = scipy.stats.gamma(a=a, loc=loc, scale=scale)
        np.testing.assert_allclose(trans.gamma_pdf_vectorized(x, a=a, loc=loc, scale=scale), scipy_gamma.pdf(x))




                
