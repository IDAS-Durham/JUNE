import pytest
import numpy as np
from collections import defaultdict

from june.geography import SuperAreas, SuperArea

from camps.groups import Shelter, Shelters
from camps.groups import SheltersVisitsDistributor


@pytest.fixture(name="visits_world", scope="module")
def setup_shelter_visits(camps_world):
    shelter_visits_distributor = SheltersVisitsDistributor.from_config()
    shelter_visits_distributor.link_shelters_to_shelters(camps_world.super_areas)
    return camps_world


def test__shelter_links(visits_world):
    shelters_to_visit_sizes = defaultdict(int)
    for shelter in visits_world.shelters:
        if shelter.shelters_to_visit == None:
            shelters_to_visit_sizes[0] += 1
        else:
            shelters_to_visit_sizes[len(shelter.shelters_to_visit)] += 1
            for shelter in shelter.shelters_to_visit:
                assert isinstance(shelter, Shelter)

    assert set(shelters_to_visit_sizes.keys()) == set([0, 1, 2, 3])
    for i in shelters_to_visit_sizes.values():
        for j in shelters_to_visit_sizes.values():
            assert np.isclose(i, j, rtol=0.11)


def test__shelter_get_candidates(camps_world):
    shelter_visits_distributor = SheltersVisitsDistributor.from_config()
    for i in range(50):
        shelter = camps_world.shelters[i]
        possible_venues = shelter_visits_distributor.get_possible_venues_for_household(
            shelter
        )
        if shelter.shelters_to_visit is None:
            assert possible_venues == ()
        else:
            assert possible_venues == shelter.shelters_to_visit
