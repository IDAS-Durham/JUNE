import pytest

from june.distributors import HospitalDistributor, WorkerDistributor
from june.geography import Geography
from june.groups import Hospital, Hospitals
from june.demography.person import Person

@pytest.fixture(name="medic")
def make_medic():
    medic = Person()
    medic.sector = 'Q'
    medic.sub_sector = "Hospital"
    return medic

@pytest.fixture(name="geography_hospital")
def make_geography(medic):
    geography = Geography.from_file({"msoa": ["E02003999", "E02006764"]})
    geography.super_areas.members[0].add_worker(medic)
    return geography

def test__distribution_of_medics(geography_hospital):
    hospitals = Hospitals.for_geography(geography_hospital)
    geography_hospital.hospitals = hospitals
    hospital_distributor = HospitalDistributor(hospitals)
    hospital_distributor.distribute_medics_to_super_areas(geography_hospital.super_areas)
    non_empty_hospital = False
    for hospital in hospitals:
        if len(hospital.subgroups[Hospital.SubgroupType.workers].people) != 0:
            non_empty_hospital=True
            break
    assert non_empty_hospital

