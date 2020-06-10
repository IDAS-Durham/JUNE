import pytest

from june.distributors import HospitalDistributor
from june.demography.geography import Geography
from june.groups import Hospital, Hospitals
from june.demography.person import Person
from june.world import World, generate_world_from_geography

from june.paths import data_path, camp_data_path

@pytest.fixture(name="medic")
def make_medic():
    medic = Person()
    medic.sector = 'Q'
    medic.sub_sector = "Hospital"
    return medic

@pytest.fixture(name="people", scope="module")
def create_people():
    n_people = 50 
    people = []
    for n in range(n_people):
        people.append(Person.from_attributes(age=40))
    for n in range(n_people):
        people.append(Person.from_attributes(age=18))

    return people 

def test__distribution_of_medics(people):
    hospitals= Hospitals.from_file(filename=camp_data_path / 'input/hospitals/hospitals.csv')
    hospital_distributor = HospitalDistributor(hospitals, medic_min_age=20, patients_per_medic=10)
    hospital_distributor.distribute_medics(people)
    non_empty_hospital = False
    for hospital in hospitals:
        patients = (hospital.n_beds + hospital.n_icu_beds)
        medics = hospital.subgroups[hospital.SubgroupType.workers].people
        for medic in medics:
            assert medic.age >= hospital_distributor.medic_min_age
        assert len(medics) == patients//hospital_distributor.patients_per_medic

