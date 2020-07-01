from june.demography.person import Person
from june.groups.leisure import HouseholdVisitsDistributor
from june.demography.geography import Geography
import numpy as np
from pytest import fixture
from june import World
from june.groups.leisure import generate_leisure_for_world
from june.groups import Household


@fixture(name="visits_distributor")
def make_dist(world_visits):
    visits_distributor = HouseholdVisitsDistributor(
        world_visits.super_areas,
        male_age_probabilities={"0-100": 0.5},
        female_age_probabilities={"0-100": 0.5},
    )
    return visits_distributor


def test__every_household_has_up_to_3_links(world_visits, visits_distributor):
    super_areas = world_visits.super_areas
    visits_distributor.link_households_to_households(super_areas)
    for super_area in super_areas:
        for area in super_area.areas:
            for household in area.households:
                if household.type in [
                    "other",
                    "communal",
                ]:
                    assert household.relatives_in_households is None
                else:
                    assert (
                        household.relatives_in_households is None
                        or len(household.relatives_in_households) <= 3
                    )
                    if household.relatives_in_households is not None:
                        for link in household.relatives_in_households:
                            assert link.residence.group.spec == "household"


@fixture(name="leisure")
def make_leisure(world_visits):
    leisure = generate_leisure_for_world(["household_visits"], world_visits)
    leisure.generate_leisure_probabilities_for_timestep(0.1, True, [])
    return leisure


def test__household_home_visits_leisure_integration(leisure):
    person1 = Person.from_attributes(sex="m", age=26)
    person2 = Person.from_attributes(sex="f", age=28)
    household1 = Household(type="family")
    household2 = Household(type="student")
    household1.add(person1)
    household2.add(person2, subgroup_type=household1.SubgroupType.young_adults)
    person1.social_venues = {"household_visits" : [household2]}
    person1.busy = False
    person2.busy = False
    person1.residence.group.relatives_in_households = (person2,)
    counter = 0
    for _ in range(100):
        subgroup = leisure.get_subgroup_for_person_and_housemates(
            person1
        )
        if subgroup is not None:
            counter += 1
            assert subgroup == person2.residence

    assert np.isclose(counter, np.random.poisson(1.0 * 0.1 * 100), atol=5)


def test__do_not_visit_dead_people(leisure):
    person = Person.from_attributes()
    person2 = Person.from_attributes()
    household = Household(type="family")
    person.social_venues = {"household_visits" : [household]}
    household.add(person)
    household.relatives_in_care_homes = [person2]
    person2.dead = True
    leisure.update_household_and_care_home_visits_targets([person])
    for _ in range(0, 100):
        household = leisure.get_subgroup_for_person_and_housemates(person)
        assert household is None
