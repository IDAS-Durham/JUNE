import datetime
import pytest

from june.groups import CareHome
from june.demography import Person, Population
#from june.policy import VaccineDistribution
from june.policy.vaccine_policy import VaccineStage, VaccineTrajectory

@pytest.fixture(name='first_dose', scope='session')
def create_first_dose():
    date = datetime.datetime(2100,1,1)
    return VaccineStage(
            date_administered=date, 
            days_to_effective=10, 
            sterilisation_efficacy=0.8, 
            symptomatic_efficacy=0.7,
            prior_sterilisation_efficacy=0.1,
            prior_symptomatic_efficacy=0.,
    )


@pytest.fixture(name='vt', scope='session')
def create_vaccine_plan():
    first_dose = VaccineStage(
            date_administered=datetime.datetime(2100,1,1), 
            days_to_effective=1, 
            sterilisation_efficacy=0.3, 
            symptomatic_efficacy=0.3,
    )
    second_dose = VaccineStage(
            date_administered=datetime.datetime(2100,1,10), 
            days_to_effective=2, 
            sterilisation_efficacy=0.7, 
            symptomatic_efficacy=0.7,
            prior_sterilisation_efficacy=0.3, 
            prior_symptomatic_efficacy=0.3,
    )
    third_dose = VaccineStage(
            date_administered=datetime.datetime(2100,1,17), 
            days_to_effective=10, 
            sterilisation_efficacy=0.9, 
            symptomatic_efficacy=0.7,
            prior_sterilisation_efficacy=0.7, 
            prior_symptomatic_efficacy=0.7,

    )
    return VaccineTrajectory(stages=[first_dose, third_dose, second_dose],)


class TestDose:
    def test__dose_init(
            self,first_dose
    ):
        assert first_dose.effective_date == datetime.datetime(2100,1,11)

    def test__effect_one_stage(
            self,first_dose
    ):
        assert first_dose.get_vaccine_efficacy(
                datetime.datetime(2100,1,1), efficacy_type='sterilisation'
        ) == first_dose.prior_sterilisation_efficacy
        assert pytest.approx(first_dose.get_vaccine_efficacy(
                datetime.datetime(2100,1,6), efficacy_type='sterilisation'
        ),0.01) == 0.4499
        assert first_dose.get_vaccine_efficacy(
                datetime.datetime(2100,1,11), efficacy_type='sterilisation'
        ) == first_dose.sterilisation_efficacy
        assert first_dose.get_vaccine_efficacy(
                datetime.datetime(2100,1,21), efficacy_type = 'sterilisation'
        ) == first_dose.sterilisation_efficacy



class TestVaccineTrajectory:
    def test__stages_ordered(
            self, vt
    ):
        assert sorted([dose.date_administered for dose in vt.stages]) == [dose.date_administered for dose in vt.stages]



    def test__is_finished(
            self, vt
    ):
        assert vt.is_finished(datetime.datetime(2100,1,25)) == False
        assert vt.is_finished(datetime.datetime(2100,1,28)) == True

    def test__time_evolution_vaccine_plan(
            self, vt
    ):
        dates = [
                datetime.datetime(2100,1,1),
                datetime.datetime(2100,1,2),
                datetime.datetime(2100,1,5),
                datetime.datetime(2100,1,12),
                datetime.datetime(2100,1,17),
                datetime.datetime(2100,1,27),
                datetime.datetime(2100,1,31),
        ]
        expected_values = [0.,0.3,0.3,0.7,0.7,0.9,0.9,]
        for (date, expected) in zip(dates,expected_values):
            assert vt.get_vaccine_efficacy(date=date,efficacy_type='sterilisation') == expected
       # Check Build vaccine plan
'''
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
            first_dose_symptomatic_efficacy={0: 0.0},
            second_dose_symptomatic_efficacy={0: 0.0},
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
            first_dose_sterilisation_efficacy={0: 0.5},
            second_dose_sterilisation_efficacy={0: 1.0},
            first_dose_symptomatic_efficacy={0: 0.0},
            second_dose_symptomatic_efficacy={0: 0.0},
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
            first_dose_sterilisation_efficacy={0: 0.5},
            second_dose_sterilisation_efficacy={0: 1.0},
            first_dose_symptomatic_efficacy={0: 0.0},
            second_dose_symptomatic_efficacy={0: 0.0},
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
            first_dose_sterilisation_efficacy={0: 0.0},
            second_dose_sterilisation_efficacy={0: 0.0},
            first_dose_symptomatic_efficacy={0: 0.5},
            second_dose_symptomatic_efficacy={0: 1.0},
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
            first_dose_sterilisation_efficacy={0: 0.0},
            second_dose_sterilisation_efficacy={0: 0.0},
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
            first_dose_sterilisation_efficacy={0: 0.3},
            second_dose_sterilisation_efficacy={0: 0.7},
            first_dose_symptomatic_efficacy={0: 0.2},
            second_dose_symptomatic_efficacy={0: 0.8},
        )
        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_effective_multiplier(0) == pytest.approx(
            0.2, 0.001
        )
        assert young_person.immunity.get_susceptibility(0) == pytest.approx(0.3, 0.001)

    def test_several_infections_update(
        self,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            group_by="age",
            group_type="20-40",
            first_dose_sterilisation_efficacy={0: 0.3, 1: 0.2},
            second_dose_sterilisation_efficacy={0: 0.7, 1: 0.3},
            first_dose_symptomatic_efficacy={0: 0.3, 1: 0.2},
            second_dose_symptomatic_efficacy={0: 0.7, 1: 0.3},
        )

        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(0) == pytest.approx(0.3, 0.001)
        assert young_person.immunity.get_susceptibility(1) == pytest.approx(0.7, 0.001)
        assert young_person.immunity.get_effective_multiplier(0) == pytest.approx(
            0.3, 0.001
        )
        assert young_person.immunity.get_effective_multiplier(1) == pytest.approx(
            0.7, 0.01
        )
'''
