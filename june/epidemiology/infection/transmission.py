import yaml
import numpy as np
import numba as nb
import sys
from typing import Optional
from math import gamma

from .trajectory_maker import CompletionTime
from june import paths

default_config_path = (
    paths.configs_path
    / "defaults/epidemiology/infection/transmission/TransmissionConstant.yaml"
)
default_gamma_config_path = (
    paths.configs_path / "defaults/epidemiology/infection/transmission/nature.yaml"
)


class Transmission:
    __slots__ = "probability"

    def __init__(self):
        self.probability = 0.0

    def update_infection_probability(self, time_from_infection):
        raise NotImplementedError()


class TransmissionConstant(Transmission):
    def __init__(self, probability=0.3):
        super().__init__()
        self.probability = probability

    @classmethod
    def from_file(
        cls, config_path: str = default_config_path
    ) -> "TransmissionConstant":
        with open(config_path) as f:
            config = yaml.safe_load(f)
        probability = CompletionTime.from_dict(config["probability"])()
        return TransmissionConstant(probability=probability)

    def update_infection_probability(self, time_from_infection):
        pass


@nb.jit(nopython=True)
def gamma_pdf(x: float, a: float, loc: float, scale: float) -> float:
    """
    Implementation of gamma PDF in numba

    Parameters
    ----------
    x:
        x variable
    a:
        shape factor
    loc:
        denominator in exponential
    scale:


    Returns
    -------
        evaluation fo gamma pdf
    """
    if x < loc:
        return 0.0
    return (
        1.0
        / gamma(a)
        * ((x - loc) / scale) ** (a - 1)
        * np.exp(-(x - loc) / scale)
        / scale
    )


@nb.jit(nopython=True)
def gamma_pdf_vectorized(x: float, a: float, loc: float, scale: float) -> float:
    """
    Implementation of gamma PDF in numba

    Parameters
    ----------
    x:
        x variable
    a:
        shape factor
    loc:
        denominator in exponential
    scale:


    Returns
    -------
        evaluation fo gamma pdf
    """
    return np.where(
        x < loc,
        0.0,
        1.0
        / gamma(a)
        * ((x - loc) / scale) ** (a - 1)
        * np.exp(-(x - loc) / scale)
        / scale,
    )


class TransmissionGamma(Transmission):
    """
    Module to simulate the infectiousness profiles found in :
        - https://www.nature.com/articles/s41591-020-0869-5
        - https://arxiv.org/pdf/2007.06602.pdf
    """

    __slots__ = ("shape", "shift", "scale", "norm", "probability")

    def __init__(
        self,
        max_infectiousness: float = 1.0,
        shape: float = 2.0,
        rate: float = 3.0,
        shift: float = -2.0,
        max_symptoms: Optional[str] = None,
        asymptomatic_infectious_factor: Optional[float] = None,
        mild_infectious_factor: Optional[float] = None,
    ):
        """
        Parameters
        ----------
        max_infectiousness:
            value of the infectiousness at its peak
        shape:
            shape parameter of the gamma distribution (a for scipy stats)
        rate:
            rate parameter of the gamma distribution (1/rate = scale for scipy stats)
        shift:
            location parameter of the gamma distribution
        max_symptoms:
            maximum symptoms the individual will develop, used to reduce the infectiousness
            of asymptomatic and mild individuals if wanted
        asymptomatic_infectious_factor:
            factor to reduce the infectiousness of asymptomatic individuals
        mild_infectious_factor:
            factor to reduce the infectiousness of mild individuals
        """
        self.shape = shape
        self.shift = shift
        self.scale = 1.0 / rate
        self.norm = max_infectiousness
        if (
            asymptomatic_infectious_factor is not None
            and mild_infectious_factor is not None
        ):
            self.norm *= self._modify_infectiousness_for_symptoms(
                max_symptoms=max_symptoms,
                asymptomatic_infectious_factor=asymptomatic_infectious_factor,
                mild_infectious_factor=mild_infectious_factor,
            )
        self.probability = 0.0

    @classmethod
    def from_file(
        cls,
        max_symptoms: str = None,
        config_path: str = default_gamma_config_path,
    ) -> "TransmissionGamma":
        """
        Generate transmission class reading parameters from config file

        Parameters
        ----------
        max_symptoms:
            maximum symptoms the individual will develop, used to reduce the infectiousness
            of asymptomatic and mild individuals if wanted
        config_path:
            path to config parameters

        Returns
        -------
            TransmissionGamma instance

        """
        with open(config_path) as f:
            config = yaml.safe_load(f)
        max_infectiousness = CompletionTime.from_dict(config["max_infectiousness"])()
        shape = CompletionTime.from_dict(config["shape"])()
        rate = CompletionTime.from_dict(config["rate"])()
        shift = CompletionTime.from_dict(config["shift"])()
        asymptomatic_infectious_factor = CompletionTime.from_dict(
            config["asymptomatic_infectious_factor"]
        )()
        mild_infectious_factor = CompletionTime.from_dict(
            config["mild_infectious_factor"]
        )()

        return cls(
            max_infectiousness=max_infectiousness,
            shape=shape,
            rate=rate,
            shift=shift,
            max_symptoms=max_symptoms,
            asymptomatic_infectious_factor=asymptomatic_infectious_factor,
            mild_infectious_factor=mild_infectious_factor,
        )

    @classmethod
    def from_file_linked_symptoms(
        cls,
        time_to_symptoms_onset: float,
        max_symptoms: str = None,
        config_path: str = default_gamma_config_path,
    ) -> "TransmissionGamma":
        """
        Generate transmission class reading parameters from config file, linked to
        the time of symptoms onset

        Parameters
        ----------
        time_to_symptoms_onset:
            time (from infection) at which the person becomes symptomatic
        max_symptoms:
            maximum symptoms the individual will develop, used to reduce the infectiousness
            of asymptomatic and mild individuals if wanted
        config_path:
            path to config parameters

        Returns
        -------
            TransmissionGamma instance

        """

        with open(config_path) as f:
            config = yaml.safe_load(f)
        max_infectiousness = CompletionTime.from_dict(config["max_infectiousness"])()
        shape = CompletionTime.from_dict(config["shape"])()
        rate = CompletionTime.from_dict(config["rate"])()
        shift = CompletionTime.from_dict(config["shift"])() + time_to_symptoms_onset
        asymptomatic_infectious_factor = CompletionTime.from_dict(
            config["asymptomatic_infectious_factor"]
        )()
        mild_infectious_factor = CompletionTime.from_dict(
            config["mild_infectious_factor"]
        )()

        return cls(
            max_infectiousness=max_infectiousness,
            shape=shape,
            rate=rate,
            shift=shift,
            max_symptoms=max_symptoms,
            asymptomatic_infectious_factor=asymptomatic_infectious_factor,
            mild_infectious_factor=mild_infectious_factor,
        )

    def update_infection_probability(self, time_from_infection: float):
        """
        Performs a probability update given time from infection

        Parameters
        ----------
        time_from_infection:
            time elapsed since person became infected
        """
        self.probability = self.norm * gamma_pdf(
            x=time_from_infection, a=self.shape, loc=self.shift, scale=self.scale
        )

    @property
    def time_at_maximum_infectivity(self) -> float:
        """
        Computes the time at which the individual is maximally infectious (in this case for
        a gamma distribution

        Returns
        -------
        t_max:
            time at maximal infectiousness
        """
        return (self.shape - 1) * self.scale + self.shift

    def _modify_infectiousness_for_symptoms(
        self,
        max_symptoms: str,
        asymptomatic_infectious_factor=None,
        mild_infectious_factor=None,
    ):
        """
        Lowers the infectiousness of asymptomatic and mild cases, by modifying
        the norm of the distribution

        Parameters
        ----------
        max_symptoms:
            maximum symptom severity the person will ever have
        asymptomatic_infectious_factor:
            factor to reduce the infectiousness of asymptomatic individuals
        mild_infectious_factor:
            factor to reduce the infectiousness of mild individuals
        """
        if (
            asymptomatic_infectious_factor is not None
            and max_symptoms == "asymptomatic"
        ):
            return asymptomatic_infectious_factor
        elif mild_infectious_factor is not None and max_symptoms == "mild":
            return mild_infectious_factor
        return 1.0
