import pytest

from june.distributors import HospitalDistributor
from june.geography import Geography
from june.groups import Hospital, Hospitals
from june.demography.person import Person
from june.world import World, generate_world_from_geography

from june.paths import data_path


@pytest.fixture(name="young_medic")
def make_medic_young():
    medic = Person.from_attributes(age=18)
    medic.sector = "Q"
    medic.sub_sector = "Hospital"
    return medic


@pytest.fixture(name="old_medic")
def make_medic_old():
    medic = Person.from_attributes(age=40)
    medic.sector = "Q"
    medic.sub_sector = "Hospital"
    return medic


@pytest.fixture(name="geography_hospital")
def make_geography(young_medic, old_medic):
    geography = Geography.from_file({"super_area": ["E02003999", "E02006764"]})
    for _ in range(200):
        geography.super_areas.members[0].add_worker(young_medic)
        geography.super_areas.members[0].areas[0].add(young_medic)
    for _ in range(200):
        geography.super_areas.members[0].add_worker(old_medic)
        geography.super_areas.members[0].areas[0].add(old_medic)
    return geography


@pytest.fixture(name="hospitals")
def make_hospitals(geography_hospital):
    super_area_test = geography_hospital.super_areas.members[0]
    hospitals = [
        Hospital(
            n_beds=40,
            n_icu_beds=5,
            area=super_area_test.areas[0],
            coordinates=super_area_test.coordinates,
        ),
        Hospital(
            n_beds=80,
            n_icu_beds=20,
            area=super_area_test.areas[0],
            coordinates=super_area_test.coordinates,
        ),
    ]
    return Hospitals(hospitals)


def test__distribution_of_medics(geography_hospital, hospitals):
    geography_hospital.hospitals = hospitals
    hospital_distributor = HospitalDistributor(
        hospitals, medic_min_age=25, patients_per_medic=10, healthcare_sector_label="Q"
    )
    hospital_distributor.distribute_medics_to_super_areas(
        geography_hospital.super_areas
    )
    for hospital in hospitals:
        patients = hospital.n_beds + hospital.n_icu_beds
        medics = hospital.subgroups[hospital.SubgroupType.workers].people
        for medic in medics:
            assert medic.age >= hospital_distributor.medic_min_age
        assert len(medics) == patients // hospital_distributor.patients_per_medic


def test__distribution_of_medics_from_world(geography_hospital, hospitals):

    hospital_distributor = HospitalDistributor(
        hospitals, medic_min_age=20, patients_per_medic=10
    )
    hospital_distributor.distribute_medics_from_world(
        geography_hospital.super_areas.members[0].people
    )
    for hospital in hospitals:
        patients = hospital.n_beds + hospital.n_icu_beds
        medics = hospital.subgroups[hospital.SubgroupType.workers].people
        for medic in medics:
            assert medic.age >= hospital_distributor.medic_min_age
        assert len(medics) == patients // hospital_distributor.patients_per_medic
