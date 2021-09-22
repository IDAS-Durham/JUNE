import pytest
import numpy as np
from copy import deepcopy

from june.groups import Group
from june.geography import Area, SuperArea, Region
from june.demography.person import Person
from june.epidemiology.infection.infection_selector import InfectionSelector
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
from june.groups.school import _translate_school_subgroup
from june.groups.group.interactive import InteractiveGroup
from june import paths

test_config = paths.configs_path / "tests/interaction.yaml"


class TestInteractiveGroup:
    def test__substract_information_from_group(self, selector):
        hospital = Hospital(n_beds=None, n_icu_beds=None)
        person1 = Person.from_attributes()
        person2 = Person.from_attributes()
        person3 = Person.from_attributes()
        person4 = Person.from_attributes()
        person1.immunity.susceptibility_dict[1] = 0.1
        person2.immunity.susceptibility_dict[2] = 0.2
        person3.immunity.susceptibility_dict[3] = 0.3
        person4.immunity.susceptibility_dict[4] = 0.4
        hospital.add(person1, subgroup_type=0)
        hospital.add(person2, subgroup_type=0)
        hospital.add(person3, subgroup_type=1)
        hospital.add(person4, subgroup_type=2)
        selector.infect_person_at_time(person1, 1)
        person1.infection.update_health_status(5, 5)
        interactive_group = InteractiveGroup(hospital)
        assert (
            person1.infection.infection_id()
            in interactive_group.infectors_per_infection_per_subgroup
        )
        assert interactive_group.infectors_per_infection_per_subgroup[
            person1.infection.infection_id()
        ][0]["ids"] == [person1.id]
        assert interactive_group.infectors_per_infection_per_subgroup[
            person1.infection.infection_id()
        ][0]["trans_probs"] == [person1.infection.transmission.probability]
        assert len(interactive_group.susceptibles_per_subgroup[0]) == 1
        assert interactive_group.susceptibles_per_subgroup[0][person2.id][2] == 0.2
        assert len(interactive_group.susceptibles_per_subgroup[1]) == 1
        assert interactive_group.susceptibles_per_subgroup[1][person3.id][3] == 0.3
        assert len(interactive_group.susceptibles_per_subgroup[2]) == 1
        assert interactive_group.susceptibles_per_subgroup[2][person4.id][4] == 0.4
        assert interactive_group.must_timestep

    def test__no_timestep(self, selector):
        hospital = Hospital(n_beds=None, n_icu_beds=None)
        person1 = Person.from_attributes()
        person2 = Person.from_attributes()
        person3 = Person.from_attributes()
        person4 = Person.from_attributes()
        person1.immunity.susceptibility_dict[1] = 0.1
        person2.immunity.susceptibility_dict[2] = 0.2
        person3.immunity.susceptibility_dict[3] = 0.3
        person4.immunity.susceptibility_dict[4] = 0.4
        hospital.add(person1, subgroup_type=0)
        hospital.add(person2, subgroup_type=0)
        hospital.add(person3, subgroup_type=1)
        hospital.add(person4, subgroup_type=2)
        interactive_group = InteractiveGroup(hospital)
        assert interactive_group.has_susceptible
        assert not interactive_group.has_infectors
        assert not interactive_group.must_timestep

        hospital.clear()
        hospital.add(person1, subgroup_type=0)
        selector.infect_person_at_time(person1, 1)
        person1.infection.update_health_status(5, 5)
        interactive_group = InteractiveGroup(hospital)
        assert not interactive_group.has_susceptible
        assert interactive_group.has_infectors
        assert not interactive_group.must_timestep


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
        school = School(age_min=age_min, age_max=age_max)
        int_school = InteractiveSchool(school)
        int_school.school_years = school_years
        contact_matrix = interaction.contact_matrices["school"]
        contact_matrix = int_school.get_processed_contact_matrix(contact_matrix)
        n_contacts_same_year = contact_matrix[4, 4]
        assert n_contacts_same_year == 2.875 * 3

        n_contacts_year_above = contact_matrix[4, 5]
        assert n_contacts_year_above == xi * 2.875 * 3

        n_contacts_teacher_teacher = contact_matrix[0, 0]
        assert n_contacts_teacher_teacher == 5.25 * 3

        n_contacts_teacher_student = contact_matrix[0, 4]

        np.isclose(
            n_contacts_teacher_student, (16.2 * 3 / len(school_years)), rtol=1e-6
        )

        n_contacts_student_teacher = contact_matrix[4, 0]
        assert n_contacts_student_teacher == 0.81 * 3 / len(school_years)

    def test__school_contact_matrices_different_classroom(self):
        interaction_instance = Interaction.from_file(config_filename=test_config)
        xi = 0.3
        age_min = 3
        age_max = 7
        school_years = (3, 4, 4, 5)
        school = School(age_min=age_min, age_max=age_max)
        school.years = school_years
        int_school = InteractiveSchool(school)
        int_school.school_years = school_years
        contact_matrix = interaction_instance.contact_matrices["school"]
        contact_matrix = int_school.get_processed_contact_matrix(contact_matrix)
        n_contacts_same_year = contact_matrix[2, 3]
        n_contacts_same_class = contact_matrix[2, 2]
        assert np.isclose(n_contacts_same_year, n_contacts_same_class / 4)

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

    def test__social_distancing_primary_secondary(self):
        beta_reductions = {"school" : 0.2, "primary_school": 0.3, "secondary_school" : 0.4}
        betas = {"school" : 3.0}

        school = School(sector = "primary")
        int_school = InteractiveSchool(school)
        processed_beta = int_school.get_processed_beta(betas=betas, beta_reductions=beta_reductions)
        assert np.isclose(processed_beta, 3 * 0.3)

        school = School(sector = "secondary")
        int_school = InteractiveSchool(school)
        processed_beta = int_school.get_processed_beta(betas=betas, beta_reductions=beta_reductions)
        assert np.isclose(processed_beta, 3 * 0.4)

        school = School(sector = "primary_secondary")
        int_school = InteractiveSchool(school)
        processed_beta = int_school.get_processed_beta(betas=betas, beta_reductions=beta_reductions)
        assert np.isclose(processed_beta, 3 * 0.4)

        school = School(sector = None)
        int_school = InteractiveSchool(school)
        processed_beta = int_school.get_processed_beta(betas=betas, beta_reductions=beta_reductions)
        assert np.isclose(processed_beta, 3 * 0.2)

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
        betas = {"household": 1, "household_visits": 2}
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
