from june.infection.transmission import Transmission
import numpy as np
import numba as nb


@nb.jit(nopython=True)
def f(t, n, alpha):
    return t ** n * np.exp(-t / alpha)


@nb.jit(nopython=True)
def update_probability(time, incubation_time, norm, norm_time, alpha, n):
    if time > incubation_time:
        delta_tau = (time - incubation_time) / norm_time
        return norm * delta_tau ** n * np.exp(-delta_tau / alpha)
    else:
        return 0.0


class TransmissionXNExp(Transmission):
    def __init__(
        self, max_probability=1.0, incubation_time=2.6, norm_time=1.0, N=1.0, alpha=5.0
    ):
        self.max_probability = max_probability
        self.incubation_time = incubation_time
        self.norm_time = norm_time
        self.N = N
        self.alpha = alpha
        max_time = self.N * self.alpha * self.norm_time
        self.norm = self.max_probability / f(
            max_time / self.norm_time, self.N, self.alpha
        )  # self.f(max_time/self.norm_time)  #/self.norm_time)
        self.probability = 0.0

    def update_probability_from_delta_time(self, delta_time):
        return update_probability(
            delta_time,
            self.incubation_time,
            self.norm,
            self.norm_time,
            self.alpha,
            self.N,
        )
        # if delta_time<=self.incubation_time:
        #   self.probability = 0.
        # else:
        #   delta_tau = (delta_time - self.incubation_time)/self.norm_time
        #   self.probability = self.norm * self.f(delta_tau)

    # def f(self,t):
    #    return t**self.N * np.exp(-t/self.alpha)
