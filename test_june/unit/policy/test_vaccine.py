import datetime

from june.groups import CareHome
from june.demography import Person, Population
from june.policy import VaccineDistribution


class TestVaccination:
    def test__process_target_population(self,):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            group_description={"by": "age", "group": "20-40", "total_group_size": 100}
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan.first_dose_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan is None

    def test__process_target_population_care_home(self,):
        care_home = CareHome()
        person = Person.from_attributes(age=30, sex="f")
        care_home.add(person)
        vaccine_policy = VaccineDistribution(
            group_description={
                "by": "residence",
                "group": "care_home",
                "total_group_size": 100,
            }
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan.first_dose_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan is None

    def test__susceptibility(self,):
        person = Person.from_attributes(age=30, sex="f")
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy = VaccineDistribution(
            group_description={"by": "age", "group": "20-40", "total_group_size": 100}
        )
        vaccine_policy.apply(person=person, date=date)
        assert person.susceptibility == 1.0
        person.vaccine_plan.first_dose_date = date
        person.vaccine_plan.first_dose_effective_days = 10
        person.vaccine_plan.second_dose_date = date + datetime.timedelta(days=20)
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2100, 1, 6)
        )
        assert 0.5 < person.susceptibility < 1.0
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2100, 1, 15)
        )
        assert person.susceptibility == 0.5

        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2220, 12, 25)
        )
        assert person.susceptibility == 0.0

    def test_overall_susceptibility_update(self,):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_description={"by": "age", "group": "20-40", "total_group_size": 100}
        )
        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_susceptibility_of_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )

        assert young_person.id in vaccine_policy.vaccinated_ids
        assert young_person.susceptibility == 0.0
        assert old_person.susceptibility == 1.0
        vaccine_policy.update_susceptibility_of_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.susceptibility == 0.0

    def test_overall_susceptibility_update_no_second_dose(self,):
        young_person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            group_description={"by": "age", "group": "20-40", "total_group_size": 100}
        )
        people = Population([young_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2020, 11, 15))
        young_person.vaccine_plan.second_dose_date = None
        vaccine_policy.update_susceptibility_of_vaccinated(
            people=people, date=datetime.datetime(2020, 12, 31)
        )

        assert young_person.id in vaccine_policy.vaccinated_ids
        assert young_person.susceptibility == 0.5
        vaccine_policy.update_susceptibility_of_vaccinated(
            people=people, date=datetime.datetime(2021, 12, 31)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.susceptibility == 0.5
