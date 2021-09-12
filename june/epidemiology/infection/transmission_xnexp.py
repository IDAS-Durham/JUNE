from .transmission import Transmission
from .trajectory_maker import CompletionTime
from .symptom_tag import SymptomTag
from june import paths
import yaml
import numpy as np
import numba as nb

default_config_path = paths.configs_path / "defaults/epidemiology/infection/transmission/XNExp.yaml"


@nb.jit(nopython=True)
def xnexp(x: float, n: float, alpha: float) -> float:
    """
    Implementation of x^n exp(-x/alpha)

    Parameters
    ----------
    x:
        x variable
    n:
        exponent of x
    alpha:
        denominator in exponential

    Returns
    -------
        evaluation fo xnexp function
    """
    return x ** n * np.exp(-x / alpha)


@nb.jit(nopython=True)
def update_probability(
    time_from_infection: float,
    time_first_infectious: float,
    norm: float,
    norm_time: float,
    alpha: float,
    n: float,
) -> float:
    """
    Determines how the infectiousness profile is updated over time

    Parameters
    ----------
    time_from_infection:
        time from infection
    time_first_infectious:
        time from infection at which the person becomes infectious 
    norm:
        multiplier to the infectiousness profile
    norm_time:
        controls the definition of tau
    alpha: 
        demominator in exponential for xnexp function
    n:
        exponent of x in xnexp

    Returns
    -------
        Value of infectiousness at time 
    """

    if time_from_infection > time_first_infectious:
        delta_tau = (time_from_infection - time_first_infectious) / norm_time
        return norm * xnexp(x=delta_tau, n=n, alpha=alpha)
    else:
        return 0.0


class TransmissionXNExp(Transmission):
    __slots__ = (
        "time_first_infectious",
        "norm_time",
        "n",
        "alpha",
        "norm",
        "probability",
    )

    def __init__(
        self,
        max_probability: float = 1.0,
        time_first_infectious: float = 2.6,
        norm_time: float = 1.0,
        n: float = 1.0,
        alpha: float = 5.0,
        max_symptoms: str = None,
        asymptomatic_infectious_factor: float = None,
        mild_infectious_factor: float = None,
    ):
        """
        Class that defines the time profile of the infectiousness to be of the form x^n exp(-x/alpha)

        Parameters
        ----------
        max_probability:
            value of the infectiousness at its peak. Used to control the number of super spreaders
        time_first_infectious:
            time at which the person becomes infectious
        norm_time:
            controls the definition of x, x = (time_from_infection - time-first_infectious)/norm_time
        n:
            exponent of x in the x^n exp(-x/alpha) function
        alpha:
            denominator in exponential
        max_symptoms:
            maximum symptoms that the person will ever have, used to lower the infectiousness of
            asymptomatic and mild cases
        asymptomatic_infectious_factor:
            multiplier that lowers the infectiousness of asymptomatic cases
        mild_infectious_factor:
            multiplier that lowers the infectiousness of mild cases

        """
        self.time_first_infectious = time_first_infectious
        self.norm_time = norm_time
        self.n = n
        self.alpha = alpha
        max_delta_time = self.n * self.alpha * self.norm_time
        max_tau = max_delta_time / self.norm_time
        self.norm = max_probability / xnexp(max_tau, self.n, self.alpha)
        self._modify_infectiousness_for_symptoms(
            max_symptoms=max_symptoms,
            asymptomatic_infectious_factor=asymptomatic_infectious_factor,
            mild_infectious_factor=mild_infectious_factor,
        )
        self.probability = 0.0

    @classmethod
    def from_file(
        cls,
        time_first_infectious: float,
        n: float,
        alpha: float,
        max_symptoms: "SymptomTag" = None,
        config_path: str = default_config_path,
    ) -> "TransmissionXNExp":
        """
        Generates transmission class from config file

        Parameters
        ----------
        time_first_infectious:
            time at which the person becomes infectious
        n:
            exponent of x in the x^n exp(-x/alpha) function
        alpha:
            denominator in exponential
        max_symptoms:
            maximum symptoms that the person will ever have, used to lower the infectiousness of
            asymptomatic and mild cases


        Returns
        -------
            class instance
        """
        with open(config_path) as f:
            config = yaml.safe_load(f)
        max_probability = CompletionTime.from_dict(config["max_probability"])()
        norm_time = CompletionTime.from_dict(config["norm_time"])()
        asymptomatic_infectious_factor = CompletionTime.from_dict(
            config["asymptomatic_infectious_factor"]
        )()
        mild_infectious_factor = CompletionTime.from_dict(
            config["mild_infectious_factor"]
        )()
        return TransmissionXNExp(
            max_probability=max_probability,
            time_first_infectious=time_first_infectious,
            norm_time=norm_time,
            n=n,
            alpha=alpha,
            max_symptoms=max_symptoms,
            asymptomatic_infectious_factor=asymptomatic_infectious_factor,
            mild_infectious_factor=mild_infectious_factor,
        )

    @classmethod
    def from_file_linked_symptoms(
        cls,
        time_to_symptoms_onset: float,
        max_symptoms: "SymptomTag" = None,
        config_path: str = default_config_path,
    ) -> "TransmissionXNExp":
        """
        Generates transmission class from config file

        Parameters
        ----------
        time_first_infectious:
            time at which the person becomes infectious
        n:
            exponent of x in the x^n exp(-x/alpha) function
        alpha:
            denominator in exponential
        max_symptoms:
            maximum symptoms that the person will ever have, used to lower the infectiousness of
            asymptomatic and mild cases


        Returns
        -------
            class instance
        """
        with open(config_path) as f:
            config = yaml.safe_load(f)
        smearing_time_first_infectious = CompletionTime.from_dict(
            config["smearing_time_first_infectious"]
        )()
        time_first_infectious = time_to_symptoms_onset + smearing_time_first_infectious
        smearing_peak_position = CompletionTime.from_dict(
            config["smearing_peak_position"]
        )()
        alpha = CompletionTime.from_dict(config["alpha"])()
        peak_position = (
            time_to_symptoms_onset - time_first_infectious + smearing_peak_position
        )
        n = peak_position / alpha
        max_probability = CompletionTime.from_dict(config["max_probability"])()
        norm_time = CompletionTime.from_dict(config["norm_time"])()
        asymptomatic_infectious_factor = CompletionTime.from_dict(
            config["asymptomatic_infectious_factor"]
        )()
        mild_infectious_factor = CompletionTime.from_dict(
            config["mild_infectious_factor"]
        )()
        return TransmissionXNExp(
            max_probability=max_probability,
            time_first_infectious=time_first_infectious,
            norm_time=norm_time,
            n=n,
            alpha=alpha,
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
            time elapsed since person became infected (in days).
        """
        self.probability = update_probability(
            time_from_infection,
            self.time_first_infectious,
            self.norm,
            self.norm_time,
            self.alpha,
            self.n,
        )

    def _modify_infectiousness_for_symptoms(
        self,
        max_symptoms: str,
        asymptomatic_infectious_factor,
        mild_infectious_factor,
    ):
        """
        Lowers the infectiousness of asymptomatic and mild cases, by modifying
        self.norm

        Parameters
        ----------
        max_symptoms:
            maximum symptom severity the person will ever have

        """
        if (
            asymptomatic_infectious_factor is not None
            and max_symptoms == "asymptomatic"
        ):
            self.norm *= asymptomatic_infectious_factor
        elif mild_infectious_factor is not None and max_symptoms == "mild":
            self.norm *= mild_infectious_factor
