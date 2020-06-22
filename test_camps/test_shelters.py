import numpy as np
import pytest

from camps.groups.shelter import Shelter, Shelters, ShelterDistributor
from june.groups import Household
from june.demography.person import Person


def test__create_shelters():
    shelter = Shelter()
    household = Household()
    person1 = Person.from_attributes()
    household.add(person1)
    shelter.add(household)
    assert len(shelter.subgroups) == 2
    assert shelter.n_families == 1
    assert shelter.n_households == 1
    n_families_area = 100
    shelters = Shelters.from_families_in_area(
        n_families_area, sharing_shelter_ratio=0.75
    )
    assert np.isclose(
        len(shelters),
        0.75 * n_families_area / 2 + 0.25 * n_families_area,
        atol=1,
        rtol=0,
    )


def test__shelter_distributor():
    n_families_area = 100
    shelters = Shelters.from_families_in_area(
        n_families_area, sharing_shelter_ratio=0.75
    )
    households = [Household() for _ in range(n_families_area)]
    for household in households:
        for _ in range(3):
            person = Person.from_attributes()
            household.add(person)

    shelter_distributor = ShelterDistributor(sharing_shelter_ratio=0.75)
    shelter_distributor.distribute_people_in_shelters(shelters, households)
    shelter_one_household = 0
    shelter_more_one_household = 0
    empty_shelters = 0
    for shelter in shelters:
        assert shelter.n_families <= 2
        if shelter.n_families > 1:
            shelter_more_one_household += 1
        elif shelter.n_families == 1:
            shelter_one_household += 1
        else:
            empty_shelters += 1
    assert np.isclose(
        shelter_one_household / len(shelters),
        0.25 / (0.25 + 0.75 / 2),
        atol=0.02,
        rtol=0,
    )
    assert np.isclose(
        shelter_more_one_household / len(shelters),
        0.75 / 2 / (0.25 + 0.75 / 2),
        atol=0.02,
        rtol=0,
    )
    assert empty_shelters == 0
