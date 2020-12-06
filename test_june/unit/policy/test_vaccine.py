import datetime

from june.groups import CareHome
from june.demography import Person
from june.policy import VaccineDistribution


class TestVaccination:
    def test__process_target_population(self,):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            group_description={"by": "age", "group": [20, 40], "total_group_size": 100}
        )
        vaccine_policy.daily_vaccine_probability = 1.0
        date = datetime.datetime(2020, 11, 15)
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
            group_description={"by": "residence", "group": 'care_home', "total_group_size": 100}
        )
        vaccine_policy.daily_vaccine_probability = 1.0
        date = datetime.datetime(2020, 11, 15)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan.first_dose_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_plan is None


    def test__susceptibility(self,):
        person = Person.from_attributes(age=30, sex="f")
        date = datetime.datetime(2020, 11, 15)
        vaccine_policy = VaccineDistribution(
            group_description={"by": "age", "group": [20, 40], "total_group_size": 100}
        )
        vaccine_policy.apply(person=person, date=date)
        assert person.susceptibility == 1.0
        person.vaccine_plan.first_dose_date = date
        person.vaccine_plan.first_dose_effective_days = 10 
        person.vaccine_plan.second_dose_date = date + datetime.timedelta(days=20)
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 11, 20)
        )
        assert 0.5 < person.susceptibility < 1.0
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 11, 26)
        )
        assert person.susceptibility == 0.5

        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 12, 25)
        )
        assert person.susceptibility == 0.0

