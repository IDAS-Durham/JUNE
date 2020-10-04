import pytest
import numpy as np 
import numba as nb
import random

from june.groups import Hospital, Hospitals, Cemeteries
from june.distributors import HospitalDistributor


from camps.paths import camp_data_path, camp_configs_path
from camps.camp_creation import generate_empty_world, populate_world, distribute_people_to_households
from camps.groups import PumpLatrines, PumpLatrineDistributor
from camps.groups import DistributionCenters, DistributionCenterDistributor
from camps.groups import Communals, CommunalDistributor
from camps.groups import FemaleCommunals, FemaleCommunalDistributor
from camps.groups import Religiouss, ReligiousDistributor
from camps.groups import Shelter, Shelters, ShelterDistributor
from camps.groups import IsolationUnit, IsolationUnits
from camps.groups import LearningCenters
from camps.distributors import LearningCenterDistributor
from camps.groups import PlayGroups, PlayGroupDistributor
from camps.groups import EVouchers, EVoucherDistributor
from camps.groups import NFDistributionCenters, NFDistributionCenterDistributor
from camps.groups import SheltersVisitsDistributor

def set_random_seed(seed=999):
    """
    Sets global seeds for testing in numpy, random, and numbaized numpy.
    """

    @nb.njit(cache=True)
    def set_seed_numba(seed):
        random.seed(seed)
        return np.random.seed(seed)

    np.random.seed(seed)
    set_seed_numba(seed)
    random.seed(seed)
    return

@pytest.fixture(name="camps_world", scope="session")
def generate_camp():
    world = generate_empty_world({"region": ["CXB-219"]})
    populate_world(world)
    # distribute people to households
    distribute_people_to_households(world)
    
    # medical facilities
    hospitals = Hospitals.from_file(
        filename=camp_data_path / "input/hospitals/hospitals.csv"
    )
    world.hospitals = hospitals
    for hospital in world.hospitals:
        hospital.area = world.areas.members[0]
    hospital_distributor = HospitalDistributor(
        hospitals, medic_min_age=20, patients_per_medic=10
    )
    world.isolation_units = IsolationUnits([IsolationUnit(area = world.areas[0])])
    hospital_distributor.distribute_medics_from_world(world.people)
    world.learning_centers = LearningCenters.for_areas(world.areas, n_shifts=4)
    world.pump_latrines = PumpLatrines.for_areas(world.areas)
    world.play_groups = PlayGroups.for_areas(world.areas)
    world.distribution_centers = DistributionCenters.for_areas(world.areas)
    world.communals = Communals.for_areas(world.areas)
    world.female_communals = FemaleCommunals.for_areas(world.areas)
    world.religiouss = Religiouss.for_areas(world.areas)
    world.e_vouchers = EVouchers.for_areas(world.areas)
    world.n_f_distribution_centers = NFDistributionCenters.for_areas(world.areas)
    
    world.shelters = Shelters.for_areas(world.areas)
    world.cemeteries = Cemeteries()
    shelter_distributor = ShelterDistributor(
        sharing_shelter_ratio=0.75
    )  # proportion of families that share a shelter
    for area in world.areas:
        shelter_distributor.distribute_people_in_shelters(area.shelters, area.households)
    
    return world
