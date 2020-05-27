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
                    assert household.associated_households is None
                elif household.type in ["family", "ya_parents", "nokids"]:
                    assert (
                        household.associated_households is None
                        or len(household.associated_households) <= 2
                    )
                    if household.associated_households is not None:
                    # for now we only allow household -> care_home
                        for link in household.associated_households:
                            assert link.subgroup_type == 2
                            assert link.group.spec == "care_home"
                else:
                    raise ValueError


def test__household_goes_visit_care_home(world_visits, visits_distributor):
    super_areas = world_visits.super_areas
    found_person = False
    for super_area in super_areas:
        for area in super_area.areas:
            for household in area.households:
                if household.associated_households is not None:
                    person = household.people[0]
                    found_person = True
                    break
            if found_person:
                break

    assert found_person
    social_venue = visits_distributor.get_social_venue_for_person(person)
    assert social_venue.group.spec == "care_home"
    assert social_venue.subgroup_type == 2  # visitors

@fixture(name="leisure")
def make_leisure(world_visits):
    leisure  = generate_leisure_for_world(["residence_visits"], world_visits)
    return leisure


def test__care_home_visits_leisure_integration(leisure):
    person1 = Person.from_attributes(sex="m", age=26)
    person2 = Person.from_attributes(sex="f", age=28)
    household = Household(type="family")
    care_home = CareHome()
    household.add(person1)
    household.add(person2)
    person1.busy = False
    person2.busy = False
    person1.residence.group.associated_households = [care_home]
    assigned = False
    for _ in range(0,100):
        subgroup = leisure.get_subgroup_for_person_and_housemates(person1, delta_time=1, is_weekend=True)
        if subgroup is not None:
            assigned = True
            assert subgroup.group.spec == "care_home"
            assert person2.leisure.group.spec == "care_home"
    assert assigned


