import datetime
import pytest

from june.groups import CareHome
from june.demography import Person, Population
from june.policy import VaccineDistribution

#TODO: Add test on mulitple vaccines

class TestVaccination:
    def test__process_target_population(
        self,
    ):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan.first_dose_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan is None

    def test__process_target_population_care_home(
        self,
    ):
        care_home = CareHome()
        person = Person.from_attributes(age=30, sex="f")
        care_home.add(person)
        vaccine_policy = VaccineDistribution(
            group_by="residence",
            group_type="care_home",
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan.first_dose_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan is None

    def test__susceptibility(
        self,
    ):
        person = Person.from_attributes(age=30, sex="f")
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0: 0.5},
            second_dose_sterilisation_efficacy={0: 1.0},
            first_dose_symptomatic_efficacy={0:0.0},
            second_dose_symptomatic_efficacy={0:0.0},
        )
        vaccine_policy.apply(person=person, date=date)
        assert person.immunity.get_susceptibility(0) == 1.0
        assert person.immunity.get_effective_multiplier(0) == 1.0
        person.vaccine_plan.first_dose_date = date
        person.vaccine_plan.first_dose_effective_days = 10
        person.vaccine_plan.second_dose_date = date + datetime.timedelta(days=20)
        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2100, 1, 6)
        )
        assert 0.5 < person.immunity.get_susceptibility(0) < 1.0
        assert person.immunity.get_effective_multiplier(0) == 1.0

        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2100, 1, 15)
        )
        assert person.immunity.get_susceptibility(0) == 0.5
        assert person.immunity.get_effective_multiplier(0) == 1.0

        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2220, 12, 25)
        )
        assert person.immunity.get_susceptibility(0) == 0.0
        assert person.immunity.get_effective_multiplier(0) == 1.0

    def test_overall_susceptibility_update(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0: 0.5},
            second_dose_sterilisation_efficacy={0: 1.0},
            first_dose_symptomatic_efficacy={0: 0.0},
            second_dose_symptomatic_efficacy={0: 0.0},
        )
        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )

        assert young_person.immunity.get_effective_multiplier(0) == 1.0
        assert young_person.immunity.get_susceptibility(0) == 0.0
        assert old_person.immunity.get_effective_multiplier(0) == 1.0
        assert old_person.immunity.get_susceptibility(0) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_effective_multiplier(0) == 1.0
        assert young_person.immunity.get_susceptibility(0) == 0.0

    def test_overall_susceptibility_update_no_second_dose(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0:0.5},
            second_dose_sterilisation_efficacy={0:1.0},
            first_dose_symptomatic_efficacy={0:0.0},
            second_dose_symptomatic_efficacy={0:0.0},
        )
        people = Population([young_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        young_person.vaccine_plan.second_dose_date = None
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )

        assert young_person.immunity.get_susceptibility(0) == 0.5
        assert young_person.immunity.get_effective_multiplier(0) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(0) == 0.5
        assert young_person.immunity.get_effective_multiplier(0) == 1.0

    def test_vaccinate_inmune(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        young_person.immunity.susceptibility_dict[0] = 0.0
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0:0.5},
            second_dose_sterilisation_efficacy={0:1.0},
            first_dose_symptomatic_efficacy={0:0.0},
            second_dose_symptomatic_efficacy={0:0.0},
        )

        people = Population([young_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        young_person.vaccine_plan.second_dose_date = None
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )

        assert young_person.immunity.get_susceptibility(0) == 0.0
        assert young_person.immunity.get_effective_multiplier(0) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(0) == 0.0

    def test_overall_multiplier_update(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0:0.0},
            second_dose_sterilisation_efficacy={0:0.0},
            first_dose_symptomatic_efficacy={0:0.5},
            second_dose_symptomatic_efficacy={0:1.0},
        )

        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )

        assert young_person.immunity.get_effective_multiplier(0) == 0.0
        assert young_person.immunity.get_susceptibility(0) == 1.0
        assert old_person.immunity.get_effective_multiplier(0) == 1.0
        assert old_person.immunity.get_susceptibility(0) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_effective_multiplier(0) == 0.0
        assert young_person.immunity.get_susceptibility(0) == 1.0

    def test_all_zeros_update(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0:0.0},
            second_dose_sterilisation_efficacy={0:0.0},
            first_dose_symptomatic_efficacy={0:0.0},
            second_dose_symptomatic_efficacy={0:0.0},
        )

        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )

        assert young_person.immunity.get_effective_multiplier(0) == 1.0
        assert young_person.immunity.get_susceptibility(0) == 1.0
        assert old_person.immunity.get_effective_multiplier(0) == 1.0
        assert old_person.immunity.get_susceptibility(0) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_effective_multiplier(0) == 1.0
        assert young_person.immunity.get_susceptibility(0) == 1.0

    def test_both_vaccines_update(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0:0.3},
            second_dose_sterilisation_efficacy={0:0.7},
            first_dose_symptomatic_efficacy={0:0.2},
            second_dose_symptomatic_efficacy={0:0.8},
        )
        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_effective_multiplier(0) == pytest.approx(0.2,0.001)
        assert young_person.immunity.get_susceptibility(0) == pytest.approx(0.3,0.001)

    def test_several_infections_update(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0:0.3, 1: 0.2},
            second_dose_sterilisation_efficacy={0:0.7, 1: 0.3},
            first_dose_symptomatic_efficacy={0:0.3, 1: 0.2},
            second_dose_symptomatic_efficacy={0:0.7, 1: 0.3},
        )

        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(0) == pytest.approx(0.3,0.001)
        assert young_person.immunity.get_susceptibility(1) == pytest.approx(0.7,0.001)
        assert young_person.immunity.get_effective_multiplier(0) == pytest.approx(0.3,0.001)
        assert young_person.immunity.get_effective_multiplier(1) == pytest.approx(0.7,0.01)



