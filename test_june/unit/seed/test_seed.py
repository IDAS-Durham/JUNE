import pandas as pd
import pytest
import numpy as np
from june.geography import Geography
from june.demography import Demography
from june.seed import Seed
from june.infection import InfectionSelector 
from pathlib import Path
path_pwd = Path(__file__)
dir_pwd  = path_pwd.parent
constant_config = dir_pwd.parent.parent.parent / "configs/defaults/infection/InfectionConstant.yaml"


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
def get_demography(geography):
    demography = Demography.for_geography(geography)
    for area in geography.areas:
        area.populate(demography)
    return demography

@pytest.fixture(name='selector', scope='module')
def create_selector():
    selector = InfectionSelector.from_file(constant_config)
    selector.recovery_rate            = 0.05
    selector.transmission_probability = 0.7
    return selector



@pytest.fixture(name='seed')
def get_seed(geography, selector, demography):
    super_area_to_region = pd.DataFrame(
            {
            'msoa': SUPER_AREA_LIST,
            'region': REGION_LIST
            }
            )
    return Seed(geography.super_areas, selector, None, super_area_to_region)


def test__filter_region(seed):
    super_areas = seed._filter_region(region='Yorkshire')

    assert len(super_areas) == 1
    assert super_areas[0].name == 'E02005815'


def test__n_infected_total(seed):
    
    super_areas = seed._filter_region(region='East of England')
    n_cases = 100
    seed.infect_super_areas(super_areas, n_cases)

    n_infected = 0
    for super_area in super_areas:
        for person in super_area.people:
            if person.health_information.infected: 
                n_infected += 1
    np.testing.assert_allclose(n_cases,n_infected, rtol=0.05)

    n_infected = 0
    for person in super_areas[1].people:
        if person.health_information.infected:
            n_infected += 1

    
    n_people_region = np.sum([len(super_area.people) for super_area in super_areas])
    np.testing.assert_allclose(n_cases/n_people_region*len(super_areas[1].people),n_infected, rtol=0.05)

