from collections import Counter
from covid.groups import *
import pickle
import pytest
import numpy as np
import pandas as pd
from pathlib import Path




def test__people_in_areas(world_ne):
    sum_in_areas = 0
    for area in world_ne.areas.members:
        sum_in_areas += len(area.subgroups[0]._people)
    assert  sum_in_areas == len(world_ne.people.members) 
