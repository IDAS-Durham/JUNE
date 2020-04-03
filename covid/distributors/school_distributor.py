import numpy as np
from random import uniform
from scipy import stats
import warnings

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class SchoolError(BaseException):
    """ class for throwing household related errors """

    pass


class SchoolDistributor:
    """
    Distributes students to different schools
    """

    def __init__(self, area):
        pass

    def distribute_kids_to_school(self):
        pass
