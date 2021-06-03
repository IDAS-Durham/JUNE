from june.epidemiology.infection import transmission as trans
from june import paths
import scipy.stats
import numpy as np
import os
import pytest

directory = os.path.dirname(os.path.realpath(__file__))


class TestTransmission:
    def test__update_probability_at_time(self):

        transmission = trans.TransmissionConstant(probability=0.3)

        assert transmission.probability == 0.3

class TestTransmissionGamma:
    def test__update_probability_at_time(self):
        max_infectiousness = 4.0
        shift = 3.0
        shape = 3.0
        rate = 2.0
        transmission = trans.TransmissionGamma(
            max_infectiousness=max_infectiousness, shape=shape, rate=rate, shift=shift
        )
        transmission.update_infection_probability((shape - 1) / rate + shift)
        avg_gamma = trans.TransmissionGamma(
            max_infectiousness=1.0, shape=shape, rate=rate, shift=shift
        )
        avg_gamma.update_infection_probability(
            avg_gamma.time_at_maximum_infectivity
        )
        true_avg_peak_infectivity = avg_gamma.probability

        assert transmission.probability / true_avg_peak_infectivity == pytest.approx(
            max_infectiousness, rel=0.01
        )

    @pytest.mark.parametrize("x", [0.0, 1, 3, 5])
    @pytest.mark.parametrize("a", [1, 3, 5])
    @pytest.mark.parametrize("loc", [0, -3, 3])
    @pytest.mark.parametrize("scale", [1, 3, 5])
    def test__gamma_pdf_implementation(self, x, a, loc, scale):
        scipy_gamma = scipy.stats.gamma(a=a, loc=loc, scale=scale)
        assert trans.gamma_pdf(x, a=a, loc=loc, scale=scale) == pytest.approx(
            scipy_gamma.pdf(x), rel=0.001
        )

    def test__gamma_pdf_vectorized(self,):
        x = np.linspace(0.0, 10.0, 100)
        a = 1.0
        loc = 1.0
        scale = 1.0
        scipy_gamma = scipy.stats.gamma(a=a, loc=loc, scale=scale)
        np.testing.assert_allclose(
            trans.gamma_pdf_vectorized(x, a=a, loc=loc, scale=scale), scipy_gamma.pdf(x)
        )
