import datetime
import pytest
import numpy as np

from june.groups import CareHome
from june.demography import Person, Population

from june.policy.vaccine_policy import (
    VaccineStage,
    VaccineTrajectory,
    VaccineDistribution,
    VaccineStagesGenerator,
)
from june.policy.vaccines import Vaccine
from june.epidemiology.infection.infection import Delta, Omicron

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()

@pytest.fixture(name="population")
def make_population():
    people = []
    for age in range(100):
        for _ in range(100):
            person = Person.from_attributes(age=age)
            people.append(person)
    return Population(people)

@pytest.fixture(name="vax_policy")
def make_policy():
    return VaccineDistribution(
        vaccine_type='Test',
        days_to_next_dose=[0,9,16],
        doses=[0,1,2],
        start_time="2021-03-01",
        end_time="2021-03-05",
        group_by="age",
        group_type="20-40",
        group_coverage=0.6,
    )


@pytest.fixture(name="vaccine", scope="session")
def create_vaccine():
    return Vaccine(
            'pfizer',
            doses=[0,1,2],
            days_to_effective = [1,2,10],
            sterilisation_efficacies = [ 
                {'Delta': {'0-100':0.3}, 'Omicron': {'0-100':0.2}},
                {'Delta': {'0-100':0.7}, 'Omicron': {'0-100':0.2}},
                {'Delta': {'0-100':0.9}, 'Omicron': {'0-100':0.8}},
            ],
            symptomatic_efficacies= [ 
                {'Delta': {'0-100':0.3}, 'Omicron': {'0-100':0.5}},
                {'Delta': {'0-100':0.7}, 'Omicron': {'0-100':0.2}},
                {'Delta': {'0-100':0.7}, 'Omicron': {'0-100':0.1}},
            ],
    )

@pytest.fixture(name="first_dose", scope="session")
def create_first_dose():
    date = datetime.datetime(2100, 1, 1)
    return VaccineStage(
        date_administered=date,
        days_to_effective=10,
        sterilisation_efficacy={0: 0.8, 1: 0.8},
        symptomatic_efficacy={0: 0.7, 1: 0.7},
        prior_sterilisation_efficacy={0: 0.1, 1: 0.1},
        prior_symptomatic_efficacy={0: 0.0, 1: 0.0},
    )


@pytest.fixture(name="stages", scope="session")
def create_stages():
    first_dose = VaccineStage(
        date_administered=datetime.datetime(2100, 1, 1),
        days_to_effective=1,
        sterilisation_efficacy={0: 0.3, 1: 0.2},
        symptomatic_efficacy={0: 0.3, 1: 0.5},
    )
    second_dose = VaccineStage(
        date_administered=datetime.datetime(2100, 1, 10),
        days_to_effective=2,
        sterilisation_efficacy={0: 0.7, 1: 0.2},
        symptomatic_efficacy={0: 0.7, 1: 0.2},
        prior_sterilisation_efficacy={0: 0.3, 1: 0.2},
        prior_symptomatic_efficacy={0: 0.3, 1: 0.5},
    )
    third_dose = VaccineStage(
        date_administered=datetime.datetime(2100, 1, 17),
        days_to_effective=10,
        sterilisation_efficacy={0: 0.9, 1: 0.8},
        symptomatic_efficacy={0: 0.7, 1: 0.1},
        prior_sterilisation_efficacy={0: 0.7, 1: 0.2},
        prior_symptomatic_efficacy={0: 0.7, 1: 0.2},
    )
    return [first_dose, third_dose, second_dose]


@pytest.fixture(name="vt", scope="session")
def create_vaccine_plan(vaccine,):
    person = Person.from_attributes(age=10, sex="f")
    person.immunity.susceptibility_dict = {delta_id: 0.9, omicron_id: 0.9}
    person.immunity.effective_multiplier_dict = {delta_id: 1.0, omicron_id: 1.0}
    return VaccineTrajectory(
        person=person,
        date_administered=datetime.datetime(2100, 1, 1),
        vaccine=vaccine,
        days_to_next_dose = [0,9,16],
    )


@pytest.fixture(name="gs", scope="session")
def create_generated_stages():
    person = Person.from_attributes(age=10, sex="f")
    date = datetime.datetime(2100, 1, 3)
    vaccine = Vaccine(
            'pfizer',
            doses=[0,1,2],
            days_to_effective = [1,2,3],
            sterilisation_efficacies = [ 
                {'Delta': {'0-100':0.2},},
                {'Delta': {'0-100':0.7},},
                {'Delta': {'0-100':0.5},},
            ],
            symptomatic_efficacies= [ 
                {'Delta': {'0-100':0.3},},
                {'Delta': {'0-100':0.6},},
                {'Delta': {'0-100':0.3},},
            ],
    )


    vg = VaccineStagesGenerator(
            vaccine=vaccine,
            days_to_next_dose = [0,10,20],

    )
    return vg(person, date)

class TestVaccine:
    def test__effective(self):
        effectiveness = [
                {'Delta': {'0-50': 0.6, '50-100': 0.7}},
                {'Delta': {'0-50': 0.8, '50-100': 0.9}},
        ]
        vaccine = Vaccine(
                'pfizer',
                doses=[0,1,2],
                days_to_effective = [0,10],
                sterilisation_efficacies = effectiveness,
                symptomatic_efficacies= effectiveness,
        )
        person = Person(age=99)
        assert vaccine.get_efficacy(person=person,dose=0, infection_id=delta_id) == (0.7,0.7)
        assert vaccine.get_efficacy_for_dose_person(person=person,dose=0,) == ({delta_id:0.7},{delta_id:0.7})
        assert vaccine.get_efficacy(person=person,infection_id=delta_id,dose=1) == (0.9,0.9)

        person = Person(age=10)
        assert vaccine.get_efficacy(person=person,infection_id=delta_id,dose=0) == (0.6,0.6)
        assert vaccine.get_efficacy(person=person,infection_id=delta_id,dose=1) == (0.8,0.8)


class TestDose:
    def test__dose_init(self, first_dose):
        assert first_dose.effective_date == datetime.datetime(2100, 1, 11)

    def test__effect_one_stage(self, first_dose):
        assert (
            first_dose.get_vaccine_efficacy(
                datetime.datetime(2100, 1, 1),
                efficacy_type="sterilisation",
                infection_id=0,
            )
            == first_dose.prior_sterilisation_efficacy[0]
        )
        assert (
            pytest.approx(
                first_dose.get_vaccine_efficacy(
                    datetime.datetime(2100, 1, 6),
                    efficacy_type="sterilisation",
                    infection_id=0,
                ),
                0.01,
            )
            == 0.4499
        )
        assert (
            first_dose.get_vaccine_efficacy(
                datetime.datetime(2100, 1, 11),
                efficacy_type="sterilisation",
                infection_id=0,
            )
            == first_dose.sterilisation_efficacy[0]
        )
        assert (
            first_dose.get_vaccine_efficacy(
                datetime.datetime(2100, 1, 21),
                efficacy_type="sterilisation",
                infection_id=0,
            )
            == first_dose.sterilisation_efficacy[0]
        )


class TestVaccineTrajectory:
    def test__stages_ordered(self, vt):
        assert sorted([dose.date_administered for dose in vt.stages]) == [
            dose.date_administered for dose in vt.stages
        ]

    def test__is_finished(self, vt):
        assert not (vt.is_finished(datetime.datetime(2100, 1, 25)))
        assert vt.is_finished(datetime.datetime(2100, 1, 28))

    def test__time_evolution_vaccine_plan(self, vt):
        dates = [
            datetime.datetime(2100, 1, 1),
            datetime.datetime(2100, 1, 2),
            datetime.datetime(2100, 1, 5),
            datetime.datetime(2100, 1, 12),
            datetime.datetime(2100, 1, 17),
            datetime.datetime(2100, 1, 27),
            datetime.datetime(2100, 1, 31),
        ]
        expected_values = [
            0.1,
            0.3,
            0.3,
            0.7,
            0.7,
            0.9,
            0.9,
        ]
        for (date, expected) in zip(dates, expected_values):
            assert (
                pytest.approx(
                    vt.get_vaccine_efficacy(
                        date=date, efficacy_type="sterilisation", infection_id=delta_id
                    )
                )
                == expected
            )

    def test__updated_vaccine_plan(self, vt):
        date = datetime.datetime(2100, 1, 27)
        susceptibility = vt.susceptibility(date=date, infection_id=delta_id)
        effective_multiplier = vt.effective_multiplier(date=date, infection_id=delta_id)
        assert pytest.approx(susceptibility, 0.001) == 0.1
        assert pytest.approx(effective_multiplier, 0.001) == 0.3


class TestVaccineStagesGenerator:
    def test__generator_dates(self, gs):
        assert gs[0].date_administered == datetime.datetime(2100, 1, 3)
        assert gs[0].effective_date == datetime.datetime(2100, 1, 4)
        assert gs[1].date_administered == datetime.datetime(2100, 1, 13)
        assert gs[1].effective_date == datetime.datetime(2100, 1, 15)
        assert gs[2].date_administered == datetime.datetime(2100, 1, 23)
        assert gs[2].effective_date == datetime.datetime(2100, 1, 26)

    def test__generator_prior_efficacies(self, gs):
        assert gs[0].prior_sterilisation_efficacy[delta_id] == 0.0
        assert gs[1].prior_sterilisation_efficacy[delta_id] == 0.2
        assert gs[2].prior_sterilisation_efficacy[delta_id] == 0.7

        assert gs[0].prior_symptomatic_efficacy[delta_id] == 0.0
        assert gs[1].prior_symptomatic_efficacy[delta_id] == 0.3
        assert gs[2].prior_symptomatic_efficacy[delta_id] == 0.6

    def test__generator_efficacies(self, gs):
        assert gs[0].sterilisation_efficacy[delta_id] == 0.2
        assert gs[1].sterilisation_efficacy[delta_id] == 0.7
        assert gs[2].sterilisation_efficacy[delta_id] == 0.5

        assert gs[0].symptomatic_efficacy[delta_id] == 0.3
        assert gs[1].symptomatic_efficacy[delta_id] == 0.6
        assert gs[2].symptomatic_efficacy[delta_id] == 0.3


class TestVaccination:
    def test__process_target_population(self,):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9,16],
            doses=[0,1,2],
            group_by="age",
            group_type="20-40",
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is not None
        assert person.vaccine_trajectory.stages[1].sterilisation_efficacy == {
            delta_id: 0.7,
            omicron_id: 0.2,
        }
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is None

    def test__process_target_population_care_home(
        self, 
    ):
        care_home = CareHome()
        person = Person.from_attributes(age=30, sex="f")
        care_home.add(person)
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9,16],
            doses=[0,1,2],
            group_by="residence",
            group_type="care_home",
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is not None
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is None

    def test__update_vaccine_effect(self,):
        person = Person.from_attributes(age=30, sex="f")
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9,16],
            doses=[0,1,2],
            group_by="age",
            group_type="20-40",
        )
        vaccine_policy.apply(person=person, date=date)
        assert person.immunity.get_susceptibility(delta_id) == 1.0
        assert person.immunity.get_effective_multiplier(delta_id) == 1.0
        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2100, 1, 2)
        )
        assert person.immunity.get_susceptibility(delta_id) == 0.7
        assert person.immunity.get_effective_multiplier(delta_id) == 0.7

        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2100, 1, 15)
        )
        assert pytest.approx(person.immunity.get_susceptibility(delta_id), 0.001) == 0.3
        assert (
            pytest.approx(person.immunity.get_effective_multiplier(delta_id), 0.001)
            == 0.3
        )

        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2220, 12, 25)
        )
        assert pytest.approx(person.immunity.get_susceptibility(delta_id), 0.001) == 0.1
        assert (
            pytest.approx(person.immunity.get_effective_multiplier(delta_id), 0.001)
            == 0.3
        )

    def test_overall_susceptibility_update(self,):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9,16],
            doses=[0,1,2],
            group_by="age",
            group_type="20-40",
        )
        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )

        assert (
            pytest.approx(
                young_person.immunity.get_effective_multiplier(delta_id), 0.001
            )
            == 0.3
        )
        assert (
            pytest.approx(young_person.immunity.get_susceptibility(delta_id), 0.001)
            == 0.1
        )
        assert old_person.immunity.get_effective_multiplier(delta_id) == 1.0
        assert old_person.immunity.get_susceptibility(delta_id) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert (
            pytest.approx(
                young_person.immunity.get_effective_multiplier(delta_id), 0.001
            )
            == 0.3
        )
        assert (
            pytest.approx(young_person.immunity.get_susceptibility(delta_id), 0.001)
            == 0.1
        )

    def test_vaccinate_inmune(
        self,  
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        young_person.immunity.susceptibility_dict[delta_id] = 0.0
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9,16],
            doses=[0,1,2],
            group_by="age",
            group_type="20-40",
        )

        people = Population([young_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )

        assert young_person.immunity.get_susceptibility(delta_id) == 0.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(delta_id) == 0.0

    def test_several_infections_update(
        self,  
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9,16],
            doses=[0,1,2],
            group_by="age",
            group_type="20-40",
        )

        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(delta_id) == pytest.approx(
            0.1, 0.001
        )
        assert young_person.immunity.get_susceptibility(omicron_id) == pytest.approx(
            0.2, 0.001
        )
        assert young_person.immunity.get_effective_multiplier(
            delta_id
        ) == pytest.approx(0.3, 0.001)
        assert young_person.immunity.get_effective_multiplier(
            omicron_id
        ) == pytest.approx(0.9, 0.01)

    def test_trajectory_doses(
        self,  
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0,9],
            doses=[0,1],
            group_by="age",
            group_type="20-40",
        )

        people = Population([young_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))

        assert person.vaccine_trajectory.get_dose_number(date=datetime.datetime(2100,1,1)) == 0 
        assert person.vaccine_trajectory.get_dose_number(date=datetime.datetime(2100,1,5)) == 0 
        assert person.vaccine_trajectory.get_dose_number(date=datetime.datetime(2100,1,10)) == 1 




class TestVaccinationInitialization:
    def test__vaccination_from_the_past(self, population, vax_policy):
        date = datetime.datetime(2021, 4, 30)
        vax_policy._apply_past_vaccinations(people=population, date=date)
        n_vaccinated = 0
        for person in population:
            if (person.age < 20) or (person.age >= 40):
                assert person.vaccinated is None 
            else:
                if person.vaccinated is not None:
                    n_vaccinated += 1
                    assert np.isclose(
                        person.vaccine_trajectory.susceptibility(date, delta_id), 0.1
                    )
                    assert np.isclose(
                        person.vaccine_trajectory.susceptibility(date, omicron_id), 0.2
                    )
                    assert np.isclose(
                        person.vaccine_trajectory.effective_multiplier(date, delta_id),
                        0.3,
                    )
                    assert np.isclose(
                        person.vaccine_trajectory.effective_multiplier(
                            date, omicron_id
                        ),
                        0.9,
                    )
        assert np.isclose(n_vaccinated, 60 * 20, atol=0, rtol=0.1)

class TestBooster:
    def test_vaccinate_booster(
        self,  
    ):
        dosed_person = Person.from_attributes(age=30, sex="f")
        not_dosed_person = Person.from_attributes(age=30, sex="f")
        dosed_person.vaccinated = 1

        vaccine_policy = VaccineDistribution(
            vaccine_type='Test',
            days_to_next_dose=[0],
            doses=[2],
            group_by="age",
            group_type="20-40",
        )

        people = Population([dosed_person, not_dosed_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 1, 30)
        )

        assert dosed_person.vaccinated == 2
        assert dosed_person.immunity.get_susceptibility(delta_id) == pytest.approx(0.1, 0.01)

        assert not_dosed_person.immunity.get_susceptibility(delta_id) == 1.
        assert not_dosed_person.vaccinated is None


class TestCoverage:
    def test__right_coverage(self, population, vax_policy):
        date = datetime.datetime(2021, 4, 30)
        start_time=datetime.datetime(2021,3,1)
        n_days = 4
        dates = [start_time+ datetime.timedelta(days=idx) for idx in range(n_days)]
        for date in dates:
            for person in population:
                vax_policy.apply(person=person, date=date)
        n_vaccinated = 0
        for person in population:
            if (person.age < 20) or (person.age >= 40):
                assert person.vaccinated is None 
            else:
                if person.vaccinated is not None:
                    n_vaccinated += 1
        print(n_vaccinated)
        assert np.isclose(n_vaccinated, 60 * 20, atol=0, rtol=0.1)



