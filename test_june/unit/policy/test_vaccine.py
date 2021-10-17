import datetime
import pytest

from june.groups import CareHome
from june.demography import Person, Population

from june.policy.vaccine_policy import (
    VaccineStage,
    VaccineTrajectory,
    VaccineDistribution,
    VaccineStagesGenerator
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
def create_vaccine_plan():
    person = Person.from_attributes(age=10, sex="f")
    person.immunity.susceptibility_dict = {0:0.9, 1:0.9}
    person.immunity.effective_multiplier_dict = {0:1., 1:1.}
    return VaccineTrajectory(
            person=person,
            date_administered=datetime.datetime(2100,1,1),
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
    )


@pytest.fixture(name='gs', scope='session')
def create_generated_stages():
    person = Person.from_attributes(age=10, sex="f")
    date = datetime.datetime(2100, 1, 3)
    vg = VaccineStagesGenerator(
            days_to_next_dose=[0,10,20],
            days_to_effective=[1,2,3],
            sterilisation_efficacies=[
                {0: 0.2},
                {0: 0.7},
                {0: 0.5},
            ],
            symptomatic_efficacies = [
                {0: 0.3},
                {0: 0.6},
                {0: 0.3},
            ],
    )
    return vg(person, date)


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
        assert vt.is_finished(datetime.datetime(2100, 1, 25)) == False
        assert vt.is_finished(datetime.datetime(2100, 1, 28)) == True

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
            assert pytest.approx(
                vt.get_vaccine_efficacy(
                    date=date, efficacy_type="sterilisation", infection_id=0
                )
            ) == expected

    def test__updated_vaccine_plan(self, vt):
        date = datetime.datetime(2100, 1, 27)
        susceptibility = vt.susceptibility(date=date, infection_id=0)
        effective_multiplier = vt.effective_multiplier(date=date, infection_id=0)
        assert pytest.approx(susceptibility, 0.001) == 0.1
        assert pytest.approx(effective_multiplier, 0.001) == 0.3


class TestVaccineStagesGenerator:
    def test__generator_dates(self, gs):
        assert gs[0].date_administered == datetime.datetime(2100,1,3)
        assert gs[0].effective_date == datetime.datetime(2100,1,4)
        assert gs[1].date_administered == datetime.datetime(2100,1,13)
        assert gs[1].effective_date == datetime.datetime(2100,1,15)
        assert gs[2].date_administered == datetime.datetime(2100,1,23)
        assert gs[2].effective_date == datetime.datetime(2100,1,26)

    def test__generator_prior_efficacies(self, gs):
        assert gs[0].prior_sterilisation_efficacy[0] == 0.
        assert gs[1].prior_sterilisation_efficacy[0] == 0.2
        assert gs[2].prior_sterilisation_efficacy[0] == 0.7

        assert gs[0].prior_symptomatic_efficacy[0] == 0.
        assert gs[1].prior_symptomatic_efficacy[0] == 0.3
        assert gs[2].prior_symptomatic_efficacy[0] == 0.6


    def test__generator_efficacies(self, gs):
        assert gs[0].sterilisation_efficacy[0] == 0.2
        assert gs[1].sterilisation_efficacy[0] == 0.7
        assert gs[2].sterilisation_efficacy[0] == 0.5

        assert gs[0].symptomatic_efficacy[0] == 0.3
        assert gs[1].symptomatic_efficacy[0] == 0.6
        assert gs[2].symptomatic_efficacy[0] == 0.3


class TestVaccination:
    def test__process_target_population(
        self,
    ):
        person = Person.from_attributes(age=30, sex="f")
        vaccine_policy = VaccineDistribution(
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
            group_by="age",
            group_type="20-40",
            infection_ids=[0,1],
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is not None
        assert person.vaccine_trajectory.stages[1].sterilisation_efficacy == {0: 0.7, 1:0.2}
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is None

    def test__process_target_population_care_home(
        self,
        stages,
    ):
        care_home = CareHome()
        person = Person.from_attributes(age=30, sex="f")
        care_home.add(person)
        vaccine_policy = VaccineDistribution(
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
            group_by="residence",
            group_type="care_home",
            infection_ids=[0,1],
        )
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is not None
        person = Person.from_attributes(age=50, sex="f")
        vaccine_policy.apply(person=person, date=date)
        assert person.vaccine_trajectory is None

    def test__update_vaccine_effect(
        self, stages
    ):
        person = Person.from_attributes(age=30, sex="f")
        date = datetime.datetime(2100, 1, 1)
        vaccine_policy = VaccineDistribution(
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
            group_by="age",
            group_type="20-40",
            infection_ids=[0,1],
       )
        vaccine_policy.apply(person=person, date=date)
        assert person.immunity.get_susceptibility(0) == 1.0
        assert person.immunity.get_effective_multiplier(0) == 1.0
        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2100, 1, 2)
        )
        assert person.immunity.get_susceptibility(0) == 0.7
        assert person.immunity.get_effective_multiplier(0) == 0.7

        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2100, 1, 15)
        )
        assert pytest.approx(person.immunity.get_susceptibility(0),0.001) == 0.3
        assert pytest.approx(person.immunity.get_effective_multiplier(0),0.001) == 0.3

        vaccine_policy.update_vaccine_effect(
            person=person, date=datetime.datetime(2220, 12, 25)
        )
        assert pytest.approx(person.immunity.get_susceptibility(0),0.001) == 0.1
        assert pytest.approx(person.immunity.get_effective_multiplier(0),0.001) == 0.3

    def test_overall_susceptibility_update(
        self, 
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
            group_by="age",
            group_type="20-40",
            infection_ids=[0,1],
        )
        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )

        assert pytest.approx(
                young_person.immunity.get_effective_multiplier(0),0.001
        ) == 0.3
        assert pytest.approx(
                young_person.immunity.get_susceptibility(0), 0.001
        ) == 0.1
        assert old_person.immunity.get_effective_multiplier(0) == 1.0
        assert old_person.immunity.get_susceptibility(0) == 1.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert pytest.approx(
                young_person.immunity.get_effective_multiplier(0),0.001
        ) == 0.3
        assert pytest.approx(
                young_person.immunity.get_susceptibility(0), 0.001
        ) == 0.1

    def test_vaccinate_inmune(
        self, stages,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        young_person.immunity.susceptibility_dict[0] = 0.0
        vaccine_policy = VaccineDistribution(
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
            group_by="age",
            group_type="20-40",
            infection_ids=[0,1],
        )

        people = Population([young_person])
        for person in people:
            vaccine_policy.apply(
                    person=person, date=datetime.datetime(2100, 1, 1)
            )
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )

        assert young_person.immunity.get_susceptibility(0) == 0.0
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 31)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(0) == 0.0

    def test_several_infections_update(
        self, stages,
    ):
        young_person = Person.from_attributes(age=30, sex="f")
        old_person = Person.from_attributes(age=80, sex="f")
        vaccine_policy = VaccineDistribution(
            days_to_next_dose=[0,9,16,],
            days_to_effective=[1,2,10],
            sterilisation_efficacies = [
                {0: 0.3, 1: 0.2},
                {0: 0.7, 1: 0.2},
                {0: 0.9, 1: 0.8},
            ],
            symptomatic_efficacies = [
                {0: 0.3, 1: 0.5},
                {0: 0.7, 1: 0.2},
                {0: 0.7, 1: 0.1},
            ],
            group_by="age",
            group_type="20-40",
            infection_ids=[0,1],
        )

        people = Population([young_person, old_person])
        for person in people:
            vaccine_policy.apply(person=person, date=datetime.datetime(2100, 1, 1))
        vaccine_policy.update_vaccinated(
            people=people, date=datetime.datetime(2100, 12, 3)
        )
        assert young_person.id not in vaccine_policy.vaccinated_ids
        assert young_person.immunity.get_susceptibility(0) == pytest.approx(0.1, 0.001)
        assert young_person.immunity.get_susceptibility(1) == pytest.approx(0.2, 0.001)
        assert young_person.immunity.get_effective_multiplier(0) == pytest.approx(
            0.3, 0.001
        )
        assert young_person.immunity.get_effective_multiplier(1) == pytest.approx(
            0.9, 0.01
        )
