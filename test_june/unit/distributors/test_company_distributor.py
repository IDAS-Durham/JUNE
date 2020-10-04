import pytest
from june.geography import SuperArea
from june.groups import Company
from june.demography import Person
from june.distributors import CompanyDistributor
from june.geography import Geography
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

def test__company_and_work_super_area(full_world):
    has_people = False
    for person in full_world.people:
        if person.work_super_area is not None:
            has_people = True
            assert person.work_super_area == person.primary_activity.group.super_area
    assert has_people


class TestLockdownStatus:
    def test__lockdown_status_random(self, full_world):
        found_worker = False
        found_child = False
        for person in full_world.areas[0].people:
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

    def test__lockdown_status_teacher(self, full_world):
        teacher = full_world.schools[0].teachers.people[0]
        assert teacher.lockdown_status == "key_worker"

    def test__lockdown_status_medic(self, full_world):
        medic = full_world.hospitals[0].people[0]
        assert medic.lockdown_status == "key_worker"

    def test__lockdown_status_care_home(self, full_world):
        care_home_worker = full_world.care_homes[0].people[0]
        assert care_home_worker.lockdown_status == "key_worker"
