from june.demography.person import Person
from june.groups.leisure import VisitsDistributor
from june.demography.geography import Geography
from june.groups import CareHomes
import numpy as np
from pytest import fixture
from june import World
from june.groups.leisure import generate_leisure_for_world
from june.groups import Household, CareHome


@fixture(name="world_visits", scope="module")
def make_super_areas():
    geo = Geography.from_file({"msoa": ["E02003353"]})
    geo.care_homes = CareHomes.for_geography(geo)
    world = World.from_geography(geo, include_households=True)
    return world


@fixture(name="visits_distributor")
def make_dist(world_visits):
    visits_distributor = VisitsDistributor(
        world_visits.super_areas,
        male_age_probabilities={"0-99": 1.0},
        female_age_probabilities={"0-99": 1.0},
    )
    return visits_distributor


def test__every_household_has_up_to_2_links(world_visits, visits_distributor):
    super_areas = world_visits.super_areas
    visits_distributor.link_households_to_care_homes(super_areas)
    for super_area in super_areas:
        for area in super_area.areas:
            for household in area.households:
                if household.type in [
                    "student",
                    "young_adults",
                    "old",
                    "other",
                    "communal",
                ]:
                    assert household.relatives is None
                elif household.type in ["family", "ya_parents", "nokids"]:
                    assert household.relatives is None or len(household.relatives) <= 2
                    if household.relatives is not None:
                        # for now we only allow household -> care_home
                        for link in household.relatives:
                            assert link.residence.subgroup_type == 1 # link is a resident
                            assert link.residence.group.spec == "care_home"
                else:
                    raise ValueError


def test__household_goes_visit_care_home(world_visits, visits_distributor):
    super_areas = world_visits.super_areas
    found_person = False
    for super_area in super_areas:
        for area in super_area.areas:
            for household in area.households:
                if household.relatives is not None:
                    person = household.people[0]
                    found_person = True
                    break
            if found_person:
                break

    assert found_person
    social_venue = visits_distributor.get_social_venue_for_person(person)
    assert social_venue.spec == "care_home"


@fixture(name="leisure")
def make_leisure(world_visits):
    leisure = generate_leisure_for_world(["residence_visits"], world_visits)
    return leisure


def test__care_home_visits_leisure_integration(world_visits, leisure):
    person1 = Person.from_attributes(sex="m", age=26)
    person2 = Person.from_attributes(sex="f", age=28)
    household = Household(type="family")
    household.add(person1)
    household.add(person2)
    person1.busy = False
    person2.busy = False
    for area in world_visits.areas:
        if area.care_home is not None:
            break
    person1.residence.group.relatives = [area.care_home.residents[0]]
    assigned = False
    for _ in range(0, 100):
        subgroup = leisure.get_subgroup_for_person_and_housemates(
            person1, delta_time=1, is_weekend=True
        )
        if subgroup is not None:
            assigned = True
            assert (
                subgroup
                == area.care_home.subgroups[area.care_home.SubgroupType.visitors]
            )
            assert subgroup.group == area.care_home
    assert assigned

def test__do_not_visit_old_people(world_visits, leisure):
    # look for a person in carehome
    found = False
    for area in world_visits.areas:
        for person in area.people:
            if person.residence.group.spec == "care_home":
                found = True
                break
    assert found
    person2 = Person.from_attributes()
    household = Household(type="family")
    household.add(person2)
    household.relatives = [person]
    person.dead = True
    for _ in range(0,100):
        care_home = leisure.get_subgroup_for_person_and_housemates(person2, 0.1, True)
        assert care_home is None

