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

@pytest.fixture(name="user_parameters")
def make_user_config():
    user_parameters = {"transmission_probability": 0.8}
    return user_parameters


def test_read_parameters_default(tdefault):
    for parameter in tdefault.required_parameters:
        assert(hasattr(tdefault, parameter))

def test_update_probability(tdefault, timer):
    tdefault.update_probability()
    assert(tdefault.last_time_updated == timer.now)

@pytest.fixture(name="tuser")
def make_transmission_constant(timer, user_parameters):
    trans = TransmissionConstant(timer, user_parameters)
    return trans

def test_read_parameters(tuser, user_parameters):
    for parameter in user_parameters.keys():
        assert(getattr(tuser, parameter) == user_parameters[parameter])








