import numpy as np
import pytest

from june.groups.leisure.residence_visits import ResidenceVisitsDistributor
from june.demography import Person
from june.groups import Household, CareHome, Pub, Company
from june.geography import SuperArea, SuperAreas, Area, Areas


@pytest.fixture(name="rv_distributor", scope="module")
def make_rvd():
    residence_visits_distributor = ResidenceVisitsDistributor(
        residence_type_probabilities={"household": 0.7, "care_home": 0.3},
        times_per_week={
            "weekday": {"male": {"0-100": 1}, "female": {"0-100": 1}},
            "weekend": {"male": {"0-100": 1}, "female": {"0-100": 1}},
        },
        hours_per_day={
            "weekday": {"male": {"0-100": 3}, "female": {"0-100": 3}},
            "weekend": {"male": {"0-100": 3}, "female": {"0-100": 3}},
        },
    )
    return residence_visits_distributor


@pytest.fixture(name="super_areas", scope="module")
def make_super_areas(rv_distributor):
    n_super_areas = 10
    n_areas_per_super_area = 5
    n_households_per_area = 10
    super_areas = []
    areas = []
    person = Person.from_attributes()
    for i in range(n_super_areas):
        areas_super_area = []
        for j in range(n_areas_per_super_area):
            area = Area(coordinates=[i, j])
            for _ in range(n_households_per_area):
                household = Household(type="family")
                household.add(person)
                area.households.append(household)
                household = Household(type="communal")
                household.add(person)
                area.households.append(household)
            area.care_home = CareHome(area=area)
            areas.append(area)
            areas_super_area.append(area)
        super_area = SuperArea(areas=areas_super_area, coordinates=[i, i])
        super_areas.append(super_area)
    super_areas = SuperAreas(super_areas)
    rv_distributor.link_households_to_households(super_areas)
    return super_areas


class TestResidenceVisitsDistributor:
    def test__get_residence_to_visit(self, rv_distributor):
        person = Person.from_attributes(age=8)
        household = Household(type="family")
        household2 = Household()
        household.add(person)
        household.residences_to_visit["household"] = (household2,)
        rv_distributor.get_leisure_group(person) == household2
        rv_distributor.get_leisure_subgroup(person) == household2[
            household2.SubgroupType.kids
        ]

    def test__no_visits_during_working_hours(self, rv_distributor):
        poisson_no_working = []
        for sex in ["m", "f"]:
            for age in range(0, 100):
                for day_type in ["weekday", "weekend"]:
                    poisson_parameter = rv_distributor.get_poisson_parameter(
                        age=age, sex=sex, day_type=day_type, working_hours=True
                    )
                    assert poisson_parameter == 0
                    poisson_parameter = rv_distributor.get_poisson_parameter(
                        age=age, sex=sex, day_type=day_type, working_hours=False
                    )
                    assert poisson_parameter > 0


class TestHouseholdVisits:
    def test__household_linking(self, super_areas):
        has_visits = False
        for super_area in super_areas:
            for area in super_area.areas:
                for household in area.households:
                    has_visits = True
                    to_visit = [
                        residence
                        for residence in household.residences_to_visit["household"]
                    ]
                    assert len(to_visit) in range(2, 5)
        assert has_visits

    def test__visitors_stay_home_when_visited(self, rv_distributor):
        visitor = Person.from_attributes(age=20)
        resident1 = Person.from_attributes()
        resident2 = Person.from_attributes()
        household_visitor = Household(type="family")
        household_visitor.add(visitor)
        household_residents = Household(type="family")
        household_residents.add(resident1)
        household_residents.add(resident2)
        household_visitor.residences_to_visit["household"] = (household_residents,)
        # resident 1 is at the pub, he can go bakc home
        pub = Pub()
        pub.add(resident1)
        assert resident1.leisure == pub[0]
        # resident 2 is at the company, he can't go back home
        company = Company()
        company.add(resident2)
        assert resident2.primary_activity == company[0]
        subgroup = rv_distributor.get_leisure_subgroup(visitor)
        assert (
            subgroup
            == household_residents[household_residents.SubgroupType.young_adults]
        )
        assert resident1.leisure == resident1.residence
        assert resident2.leisure is None


class TestCareHomeVisits:
    def test__every_resident_has_one_relative(self, super_areas, rv_distributor):
        rv_distributor.link_households_to_care_homes(super_areas)
        has_visits = False
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
                        has_visits = True
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
        assert has_visits

    def test__type_probabilities(self, rv_distributor):
        visitor = Person.from_attributes(age=20)
        household = Household(type="family")
        household2 = Household(type="family")
        care_home = CareHome()
        household.add(visitor)
        household.residences_to_visit = {
            "household": (household2,),
            "care_home": (care_home,),
        }
        gets_household = 0
        gets_care_home = 0
        for _ in range(500):
            tovisit = rv_distributor.get_leisure_group(visitor)
            assert tovisit in [household2, care_home]
            if tovisit == household2:
                gets_household += 1
            else:
                gets_care_home += 1
        total = gets_care_home + gets_household
        assert np.isclose(gets_household / total, 0.7, rtol=0.1)
        assert np.isclose(gets_care_home / total, 0.3, rtol=0.1)
