import datetime

from june.groups import CareHome
from june.demography import Person
from june.policy import VaccineDistribution


class TestVaccination:
    def test__process_target_population(self,):
        person = Person.from_attributes(age=30, sex="f")
        #person.susceptibilty = 1.
        vaccine_policy = VaccineDistribution(
            start_time = "2020-12-08",
            end_time = "2020-12-09",
            group_description={"by": "age", "group": "20-40"},
            effective_after_first_dose=1,
        )
        date = datetime.datetime(2020, 12, 8)
        vaccine_policy.apply(person=person, date=date)
        assert person.first_effective_date == date + datetime.timedelta(days=1)
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.first_effective_date is None

    def test__process_target_population_care_home(self,):
        care_home = CareHome()
        person = Person.from_attributes(age=30, sex="f")
        care_home.add(person)
        vaccine_policy = VaccineDistribution(
            start_time = "2020-12-08",
            end_time = "2020-12-09",
            group_description={"by": "residence", "group": 'care_home'},
            effective_after_first_dose=1,
        )
        date = datetime.datetime(2020, 12, 8)
        vaccine_policy.apply(person=person, date=date)
        assert person.first_effective_date == date + datetime.timedelta(days=1)
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.first_effective_date is None

    def test__susceptibility(self,):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            start_time = "2020-12-08",
            end_time = "2020-12-09",
            group_description={"by": "age", "group": "20-40"},
            efficacy=1.,
            second_dose_compliance = 1.,
            effective_after_first_dose=1,
        )
        assert person.susceptibility == 1.0
        date = datetime.datetime(2020, 12, 8)
        vaccine_policy.apply(person=person, date=date)
        assert person.first_effective_date == date + datetime.timedelta(days=1)
        assert person.second_dose_date is not None
        assert person.second_effective_date is not None

        person.first_effective_date = date + datetime.timedelta(days=10)
        person.second_dose_date = date + datetime.timedelta(days=12)
        person.second_effective_date = date + datetime.timedelta(days=15)
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 12, 10)
        )
        print (person.susceptibility)
        assert 0.0 < person.susceptibility < 1.0
        assert 1 == 0

        # make sure person as ascertainted first dose max susceptibility
        person.susceptibility = 0.5
        vaccine_policy.update_susceptibility(
            person=person, date=datetime.datetime(2020, 12, 22)
        )
        assert person.susceptibility == 0.0

