import pytest
from june.demography.geography import SuperArea
from june.groups import Company
from june.demography import Person
from june.distributors import CompanyDistributor
from june.demography.geography import Geography
from june.world import World, generate_world_from_geography
from june.groups import (
    Hospitals,
    Schools,
    Companies,
    Households,
    CareHomes,
    Universities,
    Cemeteries,
)

# TODO: This test shouldn't use from goegraphy! Create a world that has those characteristics


@pytest.fixture(name="super_area")
def make_super_area():
    super_area = SuperArea()
    for i in range(3):
        super_area.companies.append(Company(sector=i, n_workers_max=i))
        person = Person.from_attributes()
        person.sector = i
        super_area.workers.append(person)
    return super_area


def test__company_distributor(super_area):
    cd = CompanyDistributor()
    cd.distribute_adults_to_companies_in_super_area(super_area)
    for company in super_area.companies:
        assert len(company.people) == 1
        assert list(company.people)[0].sector == company.sector


@pytest.fixture(name="super_area_big", scope="module")
def create_big_geography():
    g = Geography.from_file(
        filter_key={
            "super_area": [
                "E02002560",
            ]
        }
    )
    return g


@pytest.fixture(name="company_world", scope="module")
def make_world(geography):
    geography.hospitals = Hospitals.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    geography.care_homes = CareHomes.for_geography(geography)
    geography.universities = Universities.for_super_areas(geography.super_areas)
    world = generate_world_from_geography(
        geography, include_households=False, include_commute=False
    )
    return world


class TestLockdownStatus:
    def test__lockdown_status_random(self, company_world):
        found_worker = False
        found_child = False
        for person in company_world.areas[0].people:
            if person.age > 18:
                worker = person
                found_worker = True
            elif person.age < 18:
                child = person
                found_child = True
            if found_worker and found_child:
                break

        assert worker.lockdown_status is not None
        assert child.lockdown_status is None

    def test__lockdown_status_teacher(self, company_world):
        teacher = company_world.schools[0].teachers.people[0]
        assert teacher.lockdown_status == "key_worker"

    def test__lockdown_status_medic(self, company_world):
        medic = company_world.hospitals[0].people[0]
        assert medic.lockdown_status == "key_worker"

    def test__lockdown_status_care_home(self, company_world):
        care_home_worker = company_world.care_homes[0].people[0]
        assert care_home_worker.lockdown_status == "key_worker"
