"""
A few numbaised useful functions for random sampling.
"""
from numba import jit
from random import random
import numpy as np

@jit(nopython=True)
def random_choice_numba(arr, prob):
    """
    Fast implementation of np.random.choice
    """
    return arr[np.searchsorted(np.cumsum(prob), random(), side="right")]

