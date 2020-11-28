from june.demography.person import Person
from june.groups.leisure import CareHomeVisitsDistributor
from june.geography import Geography
from june.groups import CareHomes
import numpy as np
from pytest import fixture
from june import World
from june.groups.leisure import generate_leisure_for_world
from june.groups import Household, CareHome
from june.world import generate_world_from_geography


@fixture(name="visits_distributor")
def make_dist(world_visits):
    visits_distributor = CareHomeVisitsDistributor(
        poisson_parameters={"male": {"0-99": 1.0}, "female": {"0-99": 1.0}}
    )
    visits_distributor.link_households_to_care_homes(world_visits.super_areas)
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
                    assert "care_home" not in household.residences_to_visit
                elif household.type in ["family", "ya_parents", "nokids"]:
                    assert (
                        "care_home" not in household.residences_to_visit
                        or len(household.residences_to_visit["care_home"]) <= 2
                    )
                    if "care_home" in household.residences_to_visit:
                        # for now we only allow household -> care_home
                        for link in household.residences_to_visit["care_home"]:
                            assert link.spec == "care_home"
                else:
                    raise ValueError


def test__household_goes_visit_care_home(world_visits, visits_distributor):
    super_areas = world_visits.super_areas
    found_person = False
    for super_area in super_areas:
        for area in super_area.areas:
            for household in area.households:
                if "care_home" in household.residences_to_visit:
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
    leisure = generate_leisure_for_world(["care_home_visits"], world_visits)
    leisure.distribute_social_venues_to_areas(
        world_visits.areas, super_areas=world_visits.super_areas
    )
    leisure.generate_leisure_probabilities_for_timestep(0.1, True, False)
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
    person1.residence.group.residences_to_visit["care_home"] = [area.care_home]
    assigned = False
    for _ in range(0, 100):
        subgroup = leisure.get_subgroup_for_person_and_housemates(person1)
        if subgroup is not None:
            assigned = True
            assert (
                subgroup
                == area.care_home.subgroups[area.care_home.SubgroupType.visitors]
            )
            assert subgroup.group == area.care_home
    assert assigned
