import pandas as pd
import pytest
import numpy as np
from june.geography import Geography
from june.demography import Demography
from june.seed import Seed

SUPER_AREA_LIST = [
                        'E02004940',
                        'E02004935',
                        'E02004936',
                        'E02004937',
                        'E02004939',
                        'E02005815'
                        ]
REGION_LIST = (len(SUPER_AREA_LIST)-1)*['East of England'] + ['Yorkshire']

@pytest.fixture(name='geography')
def get_geography():

    geography = Geography.from_file(
            filter_key={
                    'msoa': SUPER_AREA_LIST                     
                    }
            )
    return geography 

@pytest.fixture(name='demography')
def get_demography():
    demography = Demography.for_geography(geography)
    demography.populate(geography.areas)
    return demography


@pytest.fixture(name='seed')
def get_seed(geography):
    super_area_to_region = pd.DataFrame(
            {
            'msoa': SUPER_AREA_LIST,
            'region': REGION_LIST
            }
            )
    return Seed(geography, super_area_to_region)


def test__filter_region(seed):
    super_areas = seed._filter_region(region='Yorkshire')

    assert len(super_areas) == 1
    assert super_areas[0].name == 'E02005815'


'''
def test__n_people_region(geography, seed):
    print('Super areas')
    print(geography.super_areas.members[1].areas.values[0].people)
    super_area = geography.super_areas.members[-1]
    print('people')
    print(np.sum([len(area.people) for area in super_area.areas.values]))
    n_people_region = seed.get_n_people_region([super_area])
    print(np.sum([len(area.people) for area in super_area.areas.members]))

    assert n_people_region == np.sum([len(area.people) for area in super_area.areas.members])
'''

