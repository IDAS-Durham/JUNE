from june.demography.person import Person
from june.groups.leisure import VisitsDistributor
from june.demography.geography import Geography
import numpy as np
from pytest import fixture
from june import World

@fixture(name="super_areas")
def make_super_areas():
    geo = Geography.from_file({"msoa" : ["E02003999"]})
    world = World.from_geography(geo, include_households=True)
    return world.super_areas

@fixture(name="visits_distributor")
def make_dist(super_areas):
    visits_distributor = VisitsDistributor(super_areas, male_age_probabilities={"0-99": 1.0}, female_age_probabilities={"0-99": 1.0})
    return visits_distributor

def test__every_household_has_up_to_2_links(super_areas, visits_distributor):
    visits_distributor.link_households_to_carehomes()
    for area in super_areas.areas:
        for household in area.households:
            if household.type in ["student", "young_adults", "old", "other", "communal"]:
                assert household.associated_households is None
            elif household.type in ["family", "ya_parents", "nokids"]:
                assert len(household.associated_households) <= 2
                # for now we only allow household -> carehome
                for link in household.associated_households:
                    assert link.subgroup_type == 2
                    assert link.subgroup.group.spec == "care_home"
            else:
                raise ValueError

def test__household_goes_visit_carehome(super_areas, visits_distributor):
    found_person = False
    for area in super_areas.areas:
        for household in area.households:
            if household.associated_households is not None:
                person = household.people[0]
                found_person = True
                break
        if found_person:
            break

    social_venue = visits_distributor.get_social_venue_for_person(person)
    assert social_venue.group.spec == "care_home"
    assert social_venue.subgroup_type == 2 # visitors


 

