import pytest
import numpy as np
from copy import deepcopy

from june.groups import Group
from june.geography import Area, SuperArea, Region
from june.demography.person import Person
from june.infection.infection_selector import InfectionSelector
from june.groups import (
    Hospital,
    School,
    Pub,
    InteractiveSchool,
    InteractiveHousehold,
    Company,
    InteractiveCompany,
    Household,
)
from june.interaction import Interaction
from june.groups.school import _translate_school_subgroup, _get_contacts_in_school
from june.groups.group.interactive import InteractiveGroup
from june import paths

test_config = paths.configs_path / "tests/interaction.yaml"


def test__substract_information_from_group(selector):
    hospital = Hospital(n_beds=None, n_icu_beds=None)
    person1 = Person.from_attributes()
    person2 = Person.from_attributes()
    person3 = Person.from_attributes()
    person4 = Person.from_attributes()
    person1.susceptibility = 1
    person2.susceptibility = 2
    person3.susceptibility = 3
    person4.susceptibility = 4
    hospital.add(person1, subgroup_type=0)
    hospital.add(person2, subgroup_type=0)
    hospital.add(person3, subgroup_type=1)
    hospital.add(person4, subgroup_type=2)
    selector.infect_person_at_time(person1, 1)
    person1.infection.update_health_status(5, 5)
    person3.susceptibility = 0.0
    interactive_group = InteractiveGroup(hospital)
    assert len(interactive_group.infector_ids) == 1
    assert interactive_group.infector_ids[0][0] == person1.id
    assert (
        interactive_group.infector_transmission_probabilities[0][0]
        == person1.infection.transmission.probability
    )
    assert len(interactive_group.susceptible_ids) == 2
    assert interactive_group.susceptible_ids[0][0] == person2.id
    assert interactive_group.susceptible_ids[1][0] == person4.id
    assert interactive_group.susceptible_susceptibilities[0][0] == 2
    assert interactive_group.susceptible_susceptibilities[1][0] == 4


class TestDispatchOnGroupSpec:
    def test__dispatch(self):
        pub = Pub()
        interactive_pub = pub.get_interactive_group()
        assert interactive_pub.__class__ == InteractiveGroup
        school = School()
        interactive_school = school.get_interactive_group()
        assert interactive_school.__class__ == InteractiveSchool
        assert isinstance(interactive_school, InteractiveGroup)


class TestInteractiveSchool:
    def test__school_index_translation(self):
        age_min = 3
        age_max = 7
        school_years = tuple(range(age_min, age_max + 1))
        _translate_school_subgroup(1, school_years) == 4
        _translate_school_subgroup(5, school_years) == 8

    def test__school_contact_matrices(self):
        interaction = Interaction.from_file(config_filename=test_config)
        xi = 0.3
        age_min = 3
        age_max = 7
        school_years = tuple(range(age_min, age_max + 1))
        contact_matrix = interaction.contact_matrices["school"]
        n_contacts_same_year = _get_contacts_in_school(
            contact_matrix, school_years, 4, 4
        )
        assert n_contacts_same_year == 2.875 * 3

        n_contacts_year_above = _get_contacts_in_school(
            contact_matrix, school_years, 4, 5
        )
        assert n_contacts_year_above == xi * 2.875 * 3

        n_contacts_teacher_teacher = _get_contacts_in_school(
            contact_matrix, school_years, 0, 0
        )
        assert n_contacts_teacher_teacher == 5.25 * 3

        n_contacts_teacher_student = _get_contacts_in_school(
            contact_matrix, school_years, 0, 4
        )
        np.isclose(
            n_contacts_teacher_student, (16.2 * 3 / len(school_years)), rtol=1e-6
        )

        n_contacts_student_teacher = _get_contacts_in_school(
            contact_matrix, school_years, 4, 0
        )
        assert n_contacts_student_teacher == 0.81 * 3

    def test__school_contact_matrices_different_classroom(self):
        interaction_instance = Interaction.from_file(config_filename=test_config)
        xi = 0.3
        age_min = 3
        age_max = 7
        school_years = (3, 4, 4, 5)
        contact_matrix = interaction_instance.contact_matrices["school"]
        n_contacts_same_year = _get_contacts_in_school(
            contact_matrix, school_years, 2, 3
        )
        assert n_contacts_same_year == 0.0

    def test__contact_matrix_full(self):
        xi = 0.3
        interaction = Interaction.from_file(config_filename=test_config)
        contacts_school = interaction.contact_matrices["school"]
        for i in range(len(contacts_school)):
            for j in range(len(contacts_school)):
                if i == j:
                    if i == 0:
                        assert contacts_school[i][j] == 5.25 * 3  # 24 / 8
                    else:
                        assert contacts_school[i][j] == 2.875 * 3
                else:
                    if i == 0:
                        assert np.isclose(contacts_school[i][j], 16.2 * 3, rtol=1e-6)
                    elif j == 0:
                        assert np.isclose(
                            contacts_school[i][j], 0.81 * 3, atol=0, rtol=1e-6
                        )
                    else:
                        assert np.isclose(
                            contacts_school[i][j],
                            xi ** abs(i - j) * 2.875 * 3,
                            atol=0,
                            rtol=1e-6,
                        )


class TestInteractiveCompany:
    def test__sector_beta(self):
        bkp = deepcopy(InteractiveCompany.sector_betas)
        InteractiveCompany.sector_betas["R"] = 0.7
        company = Company(sector="R")
        interactive_company = company.get_interactive_group()
        betas = {"company": 2}
        beta_reductions = {}
        beta_processed = interactive_company.get_processed_beta(
            betas=betas, beta_reductions=beta_reductions
        )
        assert beta_processed == 2 * 0.7
        company = Company(sector="Q")
        interactive_company = company.get_interactive_group()
        betas = {"company": 2}
        beta_reductions = {}
        beta_processed = interactive_company.get_processed_beta(
            betas=betas, beta_reductions=beta_reductions
        )
        assert beta_processed == 2
        InteractiveCompany.sector_betas = bkp


class TestInteractiveHousehold:
    def test__household_visits_beta(self):
        person = Person.from_attributes()
        region = Region()
        region.regional_compliance = 1.0
        super_area = SuperArea(region=region)
        area = Area(super_area=super_area)
        household = Household(area=area)
        betas = {"household": 1, "household_visits": 3}
        interactive_household = household.get_interactive_group()
        assert interactive_household.get_processed_beta(betas, beta_reductions={}) == 1
        household.add(person, activity="leisure")
        interactive_household = household.get_interactive_group()
        assert interactive_household.get_processed_beta(betas, beta_reductions={}) == 3

    def test__household_visits_social_distancing(self):
        region = Region()
        region.regional_compliance = 1.0
        super_area = SuperArea(region=region)
        area = Area(super_area=super_area)
        household = Household(area=area)
        person = Person.from_attributes()
        household.add(person)
        betas = {"household": 1, "household_visits" : 2}
        beta_reductions = {"household": 0.5, "household_visits": 0.1}
        household.add(person)
        int_household = household.get_interactive_group()
        assert household.being_visited is False
        beta = int_household.get_processed_beta(betas, beta_reductions)
        assert beta == 0.5
        household = Household(area=area)
        household.add(person, activity="leisure")
        assert household.being_visited is True
        int_household = household.get_interactive_group()
        beta = int_household.get_processed_beta(betas, beta_reductions)
        assert np.isclose(beta, 0.2)
