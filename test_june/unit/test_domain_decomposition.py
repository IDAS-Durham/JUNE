import pytest

from june.domains import Domain
from june.groups import Subgroup, ExternalSubgroup, ExternalGroup
from june.geography.station import CityStation, InterCityStation

available_groups = [
    "companies",
    "schools",
    "pubs",
    "groceries",
    "cinemas",
    "universities",
]


@pytest.fixture(name="domains", scope="module")
def decomp(domains_world, test_results):
    world = domains_world
    world.to_hdf5(test_results / "test_domains_world.hdf5")
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
        hdf5_file_path=test_results / "test_domains_world.hdf5",
    )
    domain2 = Domain.from_hdf5(
        domain_id=1,
        super_areas_to_domain_dict=super_areas_to_domain_dict,
        hdf5_file_path=test_results / "test_domains_world.hdf5",
    )
    domains = [domain1, domain2]
    # append everyone everywhere for checks
    for person in world.people:
        for subgroup in person.subgroups.iter():
            if subgroup is not None:
                subgroup.append(person)
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
                # work super area
                if person_world.work_super_area is not None:
                    assert (
                        person_domain.work_super_area.coordinates[0]
                        == person_world.work_super_area.coordinates[0]
                    )
                    assert (
                        person_domain.work_super_area.coordinates[1]
                        == person_world.work_super_area.coordinates[1]
                    )
                    assert (
                        person_domain.work_super_area.id
                        == person_world.work_super_area.id
                    )
                for subgroup, subgroup_domain in zip(
                    person_world.subgroups.iter(), person_domain.subgroups.iter()
                ):
                    if subgroup is None:
                        assert subgroup_domain is None
                    else:
                        if subgroup.group.super_area.name not in domain_super_areas:
                            assert isinstance(subgroup_domain, ExternalSubgroup)
                            assert isinstance(subgroup_domain.group, ExternalGroup)
                            if domain_id == 0:
                                assert subgroup_domain.domain_id == 1
                            else:
                                assert subgroup_domain.domain_id == 0
                            assert subgroup_domain.group.spec == subgroup.group.spec
                            assert subgroup_domain.group_id == subgroup.group.id
                            assert (
                                subgroup_domain.subgroup_type == subgroup.subgroup_type
                            )
                        else:
                            assert isinstance(subgroup_domain, Subgroup)
                            assert subgroup_domain.group.id == subgroup.group.id
                            assert subgroup_domain.group.spec == subgroup.group.spec
                            assert (
                                subgroup_domain.subgroup_type == subgroup.subgroup_type
                            )
                            assert (
                                subgroup_domain.group.super_area.name
                                == subgroup.group.super_area.name
                            )

    def test__hospitals(self, domains_world, domains):
        assert len(domains_world.hospitals) > 0
        for hospital in domains_world.hospitals:
            for domain in domains:
                assert len(domain.hospitals) == len(domains_world.hospitals)
                domain_super_area_ids = [super_area.id for super_area in domain]
                if hospital.super_area.id in domain_super_area_ids:
                    for hospital_domain in domain.hospitals:
                        if hospital.id == hospital_domain.id:
                            assert hospital_domain.external is False
                            assert (
                                hospital.super_area.id == hospital_domain.super_area.id
                            )
                            assert hospital.trust_code == hospital_domain.trust_code
                            assert hospital.region_name == hospital_domain.region_name
                        else:
                            for hospital_domain in domain.hospitals:
                                if hospital_domain.id == domain.hospitals.id:
                                    assert hospital_domain.external
                                    assert (
                                        hospital.region_name
                                        == hospital_domain.region_name
                                    )

    def test__stations_and_cities(self, domains_world, domains):
        assert len(domains_world.cities) > 0
        assert len(domains_world.stations) > 0
        assert len(domains_world.city_transports) > 0
        assert len(domains_world.inter_city_transports) > 0
        for city in domains_world.cities:
            for domain in domains:
                assert len(domain.cities) == len(domains_world.cities)
                domain_super_area_ids = [super_area.id for super_area in domain]
                if city.super_area.id in domain_super_area_ids:
                    for city_domain in domain.cities:
                        if city.id == city_domain.id:
                            assert city_domain.external is False
                            assert city.super_area.id == city_domain.super_area.id
                            assert city.name == city_domain.name
                            assert (
                                city.internal_commuter_ids
                                == city_domain.internal_commuter_ids
                            )
                            break
                else:
                    for city_domain in domain.cities:
                        if city.id == city_domain.id:
                            assert city_domain.external
                            assert (
                                city.internal_commuter_ids
                                == city_domain.internal_commuter_ids
                            )
                            break

        for station in domains_world.stations:
            for domain in domains:
                assert len(domain.stations) == len(domains_world.stations)
                domain_super_area_ids = [super_area.id for super_area in domain]
                if station.super_area.id in domain_super_area_ids:
                    for super_area in domain.super_areas:
                        if (
                            super_area.closest_inter_city_station_for_city[
                                station.city
                            ].id
                            == station.id
                        ):
                            assert (
                                super_area.closest_inter_city_station_for_city[
                                    station.city
                                ].external
                                is False
                            )
                    for station_domain in domain.stations:
                        if station.id == station_domain.id:
                            assert station_domain.external is False
                            assert station.super_area.id == station_domain.super_area.id
                            if isinstance(station, InterCityStation):
                                assert len(station.inter_city_transports) == len(
                                    station_domain.inter_city_transports
                                )
                                for ct1, ct2 in zip(
                                    station.inter_city_transports,
                                    station_domain.inter_city_transports,
                                ):
                                    assert ct2.external is False
                                    assert ct1.id == ct2.id
                            else:
                                assert len(station.city_transports) == len(
                                    station_domain.city_transports
                                )
                                for ct1, ct2 in zip(
                                    station.city_transports,
                                    station_domain.city_transports,
                                ):
                                    assert ct2.external is False
                                    assert ct1.id == ct2.id
                            assert station.commuter_ids == station_domain.commuter_ids
                            break
                else:
                    for super_area in domain.super_areas:
                        if (
                            super_area.closest_inter_city_station_for_city[
                                station.city
                            ].id
                            == station.id
                        ):
                            assert (
                                super_area.closest_inter_city_station_for_city[
                                    station.city
                                ].external
                                is True
                            )
                    for station_domain in domain.stations:
                        if station.id == station_domain.id:
                            assert station_domain.external
                            if isinstance(station, InterCityStation):
                                for ct1, ct2 in zip(
                                    station.inter_city_transports,
                                    station_domain.inter_city_transports,
                                ):
                                    assert ct2.external
                                    assert ct1.id == ct2.id
                            else:
                                for ct1, ct2 in zip(
                                    station.city_transports,
                                    station_domain.city_transports,
                                ):
                                    assert ct2.external
                                    assert ct1.id == ct2.id
                            assert station.commuter_ids == station_domain.commuter_ids
                            break

    def test__residences_to_visit(self, domains_world, domains):
        assert len(domains_world.households) > 0
        for household in domains_world.households:
            for domain in domains:
                domain_super_area_ids = [super_area.id for super_area in domain]
                if household.super_area.id in domain_super_area_ids:
                    household_domain = domain.households.get_from_id(household.id)
                    assert household.id == household_domain.id
                    assert len(household.residences_to_visit) == len(
                        household_domain.residences_to_visit
                    )
                    assert len(household.residences_to_visit) == len(
                        household_domain.residences_to_visit
                    )
                    for rv1_spec in household.residences_to_visit:
                        for r1, r2 in zip(
                            household.residences_to_visit[rv1_spec],
                            household_domain.residences_to_visit[rv1_spec],
                        ):
                            assert r1.id == r2.id
                            assert r1.spec == r2.spec
                            if r1.super_area.id not in domain_super_area_ids:
                                assert r2.external
                            else:
                                assert not r2.external
