from covid.infection.transmission import TransmissionConstant
from covid.time import Timer
import pytest

@pytest.fixture(name="timer")
def make_timer():
    timer = Timer()
    return timer

@pytest.fixture(name="tdefault")
def make_transmission_constant_defaults(timer):
    trans = TransmissionConstant(timer)
    return trans

def test_read_parameters(tdefault):
    for parameter in tdefault.required_parameters:
        assert(hasattr(tdefault, parameter))

def test_update_probability(tdefault, timer):
    tdefault.update_probability()
    assert(tdefault.last_time_updated == timer.now)





