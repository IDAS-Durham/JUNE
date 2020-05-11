import pytest

from june.distributors import HospitalDistributor, WorkerDistributor
from june.geography import Geography
from june.groups import Hospital, Hospitals
from june.demography.person import Person

@pytest.fixture(name="medic", scope="session")
def make_medic():
    medic = Person()
    medic.industry = 'Q'
    medic.industry_specific = "Hospital"
    return medic

@pytest.fixture(name="geography", scope="module")
def make_geography(medic):
    geography = Geography.from_file({"msoa": ["E02003999", "E02006764"]})
    geography.super_areas.members[0].add_worker(medic)
    return geography

@pytest.fixture(name="hospitals", scope="module")
def make_hospitals(geography):
    hospitals = Hospitals.for_geography(geography)
    geography.hospitals = hospitals
    return hospitals


def test__distribution_of_medics(geography, hospitals, medic):
    hospital_distributor = HospitalDistributor(hospitals)
    hospital_distributor.distribute_medics_to_super_areas(geography.super_areas)
    for hospital in hospitals:
        if len(hospital.subgroups[Hospital.GroupType.workers].people) != 0:
            break
    assert hospital.subgroups[Hospital.GroupType.workers][0] == medic

