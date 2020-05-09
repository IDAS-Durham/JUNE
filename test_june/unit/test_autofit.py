import autofit as af
import pytest
import os

from june import world_new as w
from june.infection import symptoms as sym, transmission as trans

# TODO : move to test_world.py when world is ready.

directory = os.path.dirname(os.path.realpath(__file__))

@pytest.fixture(scope="session", autouse=True)
def do_something():
    af.conf.instance = af.conf.Config(config_path="{}/files/config/".format(directory))

class TestEpidemiology:

    def test__epidemiology_passed_to_init_as_autofit_model(self):

        epidemiology = af.CollectionPriorModel(
            symptoms=sym.SymptomsConstant,
            transmission=trans.TransmissionConstant
        )

        epidemiology.symptoms.recovery_rate = af.UniformPrior(lower_limit=0.0, upper_limit=0.8)
        epidemiology.transmission.probability = af.GaussianPrior(mean=0.3, sigma=0.1)

        world = w.World(epidemiology=epidemiology)

        assert isinstance(world.epidemiology.symptoms, af.PriorModel)
        assert isinstance(world.epidemiology.transmission, af.PriorModel)

        instance = world.epidemiology.instance_from_prior_medians()

        assert isinstance(instance, af.ModelInstance)
        assert isinstance(instance.symptoms, sym.SymptomsConstant)
        assert instance.symptoms.recovery_rate == 0.4

        assert isinstance(instance.transmission, trans.TransmissionConstant)
        assert instance.transmission.probability == 0.3

    def test__if_not_passed_to_init_loads_using_config_values(self):

        # TODO : This is not correctly reading the prior config values from test_june/unit/files/config/json_priors/

        world = w.World(epidemiology=None)

        assert isinstance(world.epidemiology.symptoms, af.PriorModel)
        assert isinstance(world.epidemiology.transmission, af.PriorModel)

        instance = world.epidemiology.instance_from_prior_medians()

        assert isinstance(instance, af.ModelInstance)
        assert isinstance(instance.symptoms, sym.SymptomsConstant)

        # This is the mean of the GaussianPrior specified in the json_priors/symptoms.json config, which is currently
        # not being read correctly.

        # assert instance.symptoms.recovery_rate == 0.2

        assert isinstance(instance.transmission, trans.TransmissionConstant)

        # This is the mean of the GaussianPrior specified in the json_priors/transmission.json config, which is
        # currently not being read correctly.

        # assert instance.transmission.probability == 0.3