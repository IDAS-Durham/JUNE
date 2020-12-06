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
        assert person.vaccine_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_date is None

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
        assert person.vaccine_date == date
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_date is None


    def test__susceptibility(self,):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution()
        assert person.susceptibility == 1.0
        person.vaccine_date = datetime.datetime(2020, 11, 5)
        person.effective_vaccine_date = person.vaccine_date + datetime.timedelta(
            days=10
        )
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 11, 9)
        )
        assert 0.0 < person.susceptibility < 1.0
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 11, 15)
        )
        assert person.susceptibility == 0.0

