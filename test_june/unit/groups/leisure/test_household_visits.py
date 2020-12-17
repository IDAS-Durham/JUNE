from june.demography.person import Person
from june.groups.leisure import HouseholdVisitsDistributor
from june.geography import Geography
import numpy as np
from pytest import fixture
from june import World
from june.groups.leisure import generate_leisure_for_world
from june.groups import Household
from june.groups.leisure import Pub


@fixture(name="visits_distributor")
def make_dist(world_visits):
    visits_distributor = HouseholdVisitsDistributor(
        poisson_parameters={"male": {"0-100": 0.5}, "female": {"0-100": 0.5}}
    )
    visits_distributor.link_households_to_households(world_visits.super_areas)
    return visits_distributor


def test__every_household_has_up_to_3_links(world_visits, visits_distributor):
    super_areas = world_visits.super_areas
    visits_distributor.link_households_to_households(super_areas)
    has_visits = False
    for super_area in super_areas:
        for area in super_area.areas:
            for household in area.households:
                if (
                    household.type
                    in [
                        "communal",
                    ]
                    or household.size == 0
                ):
                    assert "household" not in household.residences_to_visit
                else:
                    has_visits = True
                    assert len(household.residences_to_visit["household"]) in range(
                        1, 4
                    )
                    for household_to_visit in household.residences_to_visit[
                        "household"
                    ]:
                        assert household_to_visit.spec == "household"
    assert has_visits


@fixture(name="leisure")
def make_leisure(world_visits):
    leisure = generate_leisure_for_world(["household_visits"], world_visits)
    leisure.generate_leisure_probabilities_for_timestep(
        delta_time=0.1, is_weekend=True, working_hours=False
    )
    return leisure


def test__household_home_visits_leisure_integration(leisure):
    person1 = Person.from_attributes(sex="m", age=26)
    person2 = Person.from_attributes(sex="f", age=28)
    household1 = Household(type="family")
    household2 = Household(type="student")
    household1.add(person1)
    household2.add(person2, subgroup_type=household1.SubgroupType.young_adults)
    person1.residence.group.social_venues = {"household_visits": [household2]}
    person1.residence.group.residences_to_visit = {"household": [household2]}
    person1.busy = False
    person2.busy = False
    person1.residence.group.relatives_in_households = (person2,)
    counter = 0
    for _ in range(200):
        subgroup = leisure.get_subgroup_for_person_and_housemates(person1)
        if subgroup is not None:
            counter += 1
            assert subgroup == person2.residence
            assert subgroup.group.being_visited is True
            # small test to mimic clear_world() in Simulator
            subgroup.group.clear()
            assert subgroup.group.being_visited is False
    assert np.isclose(counter, np.random.poisson(1.0 * 0.1 * 200), rtol=5)


def test__people_stay_home_when_receiving_visits(leisure):
    leisure.generate_leisure_probabilities_for_timestep(
        0.1, is_weekend=True, working_hours=False
    )
    resident = Person.from_attributes()
    visitor = Person.from_attributes(age=95)
    resident_household = Household(type="family")
    resident_household.add(resident)
    visitor_household = Household()
    visitor_household.add(visitor)
    visitor_household.social_venues = {"household_visits": [resident_household]}
    visitor_household.residences_to_visit = {"household": [resident_household]}
    resident_household.clear()
    visitor_household.clear()
    resident.busy = False
    visitor.busy = False
    # check it removes if not busy
    for _ in range(200):
        subgroup = leisure.get_subgroup_for_person_and_housemates(visitor)
        if subgroup is not None:
            subgroup.append(visitor)
            assert visitor.leisure.subgroup_type == 3
            assert subgroup.group.spec == "household"
            assert visitor in resident_household.people
            assert resident.leisure == resident.residence
        resident.subgroups.leisure = None
        resident.busy = False
        visitor.busy = False
        visitor.subgroups.leisure = None
        resident_household.clear()
        visitor_household.clear()

    # now check if person also comes when at the pub
    pub = Pub()
    pub.add(resident)
    for _ in range(200):
        subgroup = leisure.get_subgroup_for_person_and_housemates(visitor)
        if subgroup is not None:
            subgroup.append(visitor)
            assert visitor.leisure.subgroup_type == 3
            assert subgroup.group.spec == "household"
            assert visitor in resident_household.people
            assert resident.leisure == resident.residence
        resident.subgroups.leisure = None
        resident.busy = False
        visitor.busy = False
        visitor.subgroups.leisure = None
        resident_household.clear()
        visitor_household.clear()


def test__no_visits_during_working_hours(leisure):
    leisure.generate_leisure_probabilities_for_timestep(
        1, is_weekend=True, working_hours=True
    )
    resident = Person.from_attributes()
    visitor = Person.from_attributes(age=95)
    resident_household = Household(type="family")
    resident_household.add(resident)
    visitor_household = Household()
    visitor_household.add(visitor)
    visitor_household.social_venues = {"household_visits": [resident_household]}
    visitor_household.residences_to_visit = {"household": [resident_household]}
    resident_household.clear()
    visitor_household.clear()
    for _ in range(500):
        subgroup = leisure.get_subgroup_for_person_and_housemates(visitor)
        assert subgroup is None
