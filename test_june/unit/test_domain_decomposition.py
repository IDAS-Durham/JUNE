import pytest

from june.domain import Domain
from june.groups import Subgroup

available_groups = [
    "companies",
    "schools",
    "pubs",
    "groceries",
    "cinemas",
    "universities",
    "hospitals",
]


@pytest.fixture(name="domains", scope="module")
def decomp(domains_world):
    world = domains_world
    world.to_hdf5("test_domains_world.hdf5")
    domains = []
    super_areas_to_domain_dict = {
        domains_world.super_areas[0].id: 0,
        domains_world.super_areas[1].id: 0,
        domains_world.super_areas[2].id: 1,
        domains_world.super_areas[3].id: 1,
    }
    domain1 = Domain.from_hdf5(
        domain_id=0,
        super_areas_to_domain_dict=super_areas_to_domain_dict,
        hdf5_file_path="test_domains_world.hdf5",
    )
    domain2 = Domain.from_hdf5(
        domain_id=1,
        super_areas_to_domain_dict=super_areas_to_domain_dict,
        hdf5_file_path="test_domains_world.hdf5",
    )
    domains = [domain1, domain2]
    # append everyone everywhere for checks
    for person in world.people:
        for subgroup in person.subgroups.iter():
            if subgroup is not None:
                subgroup.append(person)
    for household in world.households:
        for social_venues in household.social_venues.values():
            for social_venue in social_venues:
                for resident in household.residents:
                    subgroup = social_venue.get_leisure_subgroup(resident)
                    if subgroup is not None:
                        subgroup.append(resident)
    return domains


class TestDomainDecomposition:
    def test__super_area_decomposition(self, domains_world, domains):
        super_areas = [super_area.name for super_area in domains_world.super_areas]
        super_areas_domains = [
            super_area.name for domain in domains for super_area in domain.super_areas
        ]
        assert len(super_areas) == len(super_areas_domains)
        assert set(super_areas) == set(super_areas_domains)

    def test__people_decomposition(self, domains_world, domains):
        all_people = [person.id for person in domains_world.people]
        all_domains_people = [
            person.id for domain in domains for person in domain.people
        ]
        assert len(all_people) == len(all_domains_people)
        assert set(all_people) == set(all_domains_people)

    def test__all_groups_decomposition(self, domains_world, domains):
        for supergroup_name in available_groups:
            world_supergroup = getattr(domains_world, supergroup_name)
            for domain in domains:
                domain_super_area_names = [
                    super_area.name for super_area in domain.super_areas
                ]
                domain_supergroup = getattr(domain, supergroup_name)
                for group in world_supergroup:
                    if group.super_area.name not in domain_super_area_names:
                        assert group.id not in domain_supergroup.member_ids
                    else:
                        assert group.id in domain_supergroup.member_ids

    def test__information_about_away_groups(self, domains_world, domains):
        for domain_id, domain in enumerate(domains):
            domain_super_areas = [sa.name for sa in domain.super_areas]
            for person_domain in domain.people:
                person_world = domains_world.people.get_from_id(person_domain.id)
                for subgroup, subgroup_domain in zip(
                    person_world.subgroups.iter(), person_domain.subgroups.iter()
                ):
                    if subgroup is None:
                        assert subgroup_domain is None
                    else:
                        if subgroup.group.super_area.name not in domain_super_areas:
                            assert type(subgroup_domain) == tuple
                            if domain_id == 0:
                                assert subgroup_domain[0] == 1
                            else:
                                assert subgroup_domain[0] == 0
                            assert subgroup_domain[1] == subgroup.group.spec
                            assert subgroup_domain[2] == subgroup.group.id
                            assert subgroup_domain[3] == subgroup.subgroup_type
                        else:
                            assert type(subgroup_domain) == Subgroup
                            assert subgroup_domain.group.id == subgroup.group.id
                            assert subgroup_domain.group.spec == subgroup.group.spec
                            assert (
                                subgroup_domain.subgroup_type == subgroup.subgroup_type
                            )
                            assert (
                                subgroup_domain.group.super_area.name
                                == subgroup.group.super_area.name
                            )
