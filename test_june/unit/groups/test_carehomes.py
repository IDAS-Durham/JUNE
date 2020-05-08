from collections import Counter
import pickle
import pytest
import pandas as pd
from pathlib import Path
from june.distributors import CareHomeDistributor
from june.distributors.carehome_distributor import CareHomeError
from june.groups import Person

@pytest.fixture(name="carehomes_df")
def load_carehomes_df():
    carehomes_path = Path(__file__).parent.parent.parent.parent / "data/processed/census_data/output_area/test/carehomes.csv" 
    return pd.read_csv(carehomes_path)

@pytest.fixture(name="carehome_distributor")
def create_carehome_dist():
    carehome_dist = CareHomeDistributor()
    return carehome_dist

class MockArea:
    def __init__(self):
        self.carehome = None
        pass

def test_assertion_no_carehome_residents(carehome_distributor):
    area = MockArea()
    with pytest.raises(CareHomeError) as e:
        assert carehome_distributor.create_carehome_in_area(area, 0)
    assert str(e.value) == "No carehome residents in this area."


def test_number_carehomes(carehomes_df, carehome_distributor):
    """ 
    Check the number of schools is right
    """
    for value in carehomes_df.values[:,1]:
        area = MockArea()
        if value == 0:
            try:
                carehome_distributor.create_carehome_in_area(area, 0)
            except:
                assert area.carehome is None
        else:
            area.men_by_age = {}
            area.women_by_age = {}
            for age in range(50, 100):
                area.men_by_age[age] = []
                area.women_by_age[age] = []
                for _ in range(max(1, value / (100-65+1))):
                    man = Person(sex=0, age=age)
                    woman = Person(sex=1, age=age)
                    area.men_by_age[age].append(man)
                    area.women_by_age[age].append(woman)
            carehome_distributor.create_carehome_in_area(area, value)
            assert area.carehome is not None
            assert area.carehome.size == value
            for person in area.carehome.people:
                assert person.age >= 65

