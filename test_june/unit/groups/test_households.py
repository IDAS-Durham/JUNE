import pandas as pd
import pytest
from june.groups import Household, Households

def test__households_adding():
    household = Household()
    household2 = Household()
    household3 = Household()
    households1 = Households([household])
    households2 = Households([household2, household3])
    households3 = households1 + households2
    assert households3.members == [household, household2, household3]
