from june.infection.transmission import Transmission
from june.infection.trajectory_maker import CompletionTime
from june.infection.symptom_tag import SymptomTag
from june import paths
import yaml
import numpy as np
import numba as nb

default_config_path = paths.configs_path / "defaults/transmission/XNExp.yaml"


@nb.jit(nopython=True)
def f(t, n, alpha):
    return t ** n * np.exp(-t / alpha)


@nb.jit(nopython=True)
def update_probability(time, start_transmission, norm, norm_time, alpha, n):
    if time > start_transmission:
        delta_tau = (time - start_transmission) / norm_time
        return norm * delta_tau ** n * np.exp(-delta_tau / alpha)
    else:
        return 0.0


class TransmissionXNExp(Transmission):
    def __init__(
        self,
        max_probability=1.0,
        start_transmission=2.6,
        norm_time=1.0,
        N=1.0,
        alpha=5.0,
        max_symptoms=None,
        asymptomatic_infectious_factor=None,
        mild_infectious_factor=None,
    ):
        self.max_probability = max_probability
        self.start_transmission = start_transmission
        self.norm_time = norm_time
        self.N = N
        self.alpha = alpha
        max_time = self.N * self.alpha * self.norm_time
        self.norm = self.max_probability / f(
            max_time / self.norm_time, self.N, self.alpha
        )  
        if (
            asymptomatic_infectious_factor is not None
            and max_symptoms == SymptomTag.asymptomatic
        ):
            self.norm *= asymptomatic_infectious_factor
        elif (
            mild_infectious_factor is not None and max_symptoms == SymptomTag.influenza
        ):
            self.norm *= mild_infectious_factor
        self.probability = 0.0

    @classmethod
    def from_file(
        cls, start_transmission, N, alpha, max_symptoms = None, config_path: str = default_config_path
    ) -> "TransmissionXNExp":
        with open(config_path) as f:
            config = yaml.safe_load(f)
        max_probability = CompletionTime.from_dict(config["max_probability"])()
        norm_time = CompletionTime.from_dict(config["norm_time"])()
        return TransmissionXNExp(
            max_probability=max_probability,
            start_transmission=start_transmission,
            norm_time=norm_time,
            N=N,
            alpha=alpha,
            asymptomatic_infectious_factor=config["asymptomatic_infectious_factor"],
            mild_infectious_factor=config["mild_infectious_factor"]
        )

    def update_probability_from_delta_time(self, delta_time):
        self.probability = update_probability(
            delta_time,
            self.start_transmission,
            self.norm,
            self.norm_time,
            self.alpha,
            self.N,
        )
