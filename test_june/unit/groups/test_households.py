import pandas as pd
import pytest

from june.inputs import Inputs
from june.groups import Household, Households

def test__households_adding():
    households1 = Households()
    households1.members = [1,2,3]
    households2 = Households()
    households2.members = [4,5]
    households3 = households1 + households2
    assert households3.members == [1,2,3,4,5]

