from collections import Counter
import pickle
import pytest
import pandas as pd
from pathlib import Path
from june.groups.carehome import CareHome, CareHomes
from june.distributors import CareHomeDistributor
from june.distributors.carehome_distributor import CareHomeError
from june.demography.person import Person
from june.geography import Geography

def test__area_with_carehome():
    geography = Geography.from_file({"oa" : ["E00081795"]})
    carehomes = CareHomes.for_geography(geography)
    assert len(carehomes) == 1
    assert carehomes.members[0].n_residents == 24
    
def test__area_no_carehome(): 
    geography = Geography.from_file({"oa" : ["E00082111"]})
    carehomes = CareHomes.for_geography(geography)
    assert len(carehomes) == 0
    assert not hasattr(geography.areas.members[0], 'carehome')

