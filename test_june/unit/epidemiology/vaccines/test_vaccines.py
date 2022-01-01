import pytest
import datetime
from june.epidemiology.vaccines import Vaccine
from june.epidemiology.vaccines.vaccines import Efficacy, Dose, VaccineTrajectory

from june import Person
from june.epidemiology.infection.infection import Delta, Omicron

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()


@pytest.fixture(name="efficacy")
def make_efficacy():
    return Efficacy(
        infection={delta_id: 0.9, omicron_id: 0.2},
        symptoms={delta_id: 0.4, omicron_id: 0.1},
        waning_factor=0.5,
    )


@pytest.fixture(name="prior_efficacy")
def make_prior_efficacy():
    return Efficacy(
        infection={delta_id: 0.1, omicron_id: 0.1},
        symptoms={delta_id: 0.1, omicron_id: 0.1},
        waning_factor=0.5,
    )


@pytest.fixture(name="dose")
def make_dose(efficacy, prior_efficacy):
    return Dose(
        number=0,
        days_administered_to_effective=5,
        days_effective_to_waning=2,
        days_waning=10,
        efficacy=efficacy,
        prior_efficacy=prior_efficacy,
        date_administered=datetime.datetime(2022, 1, 1),
    )


class TestEfficacy:
    def test_waning(self, efficacy):
        assert efficacy(protection_type="infection", infection_id=delta_id) == 0.9
        assert efficacy(protection_type="symptoms", infection_id=omicron_id) == 0.1


class TestDose:
    def test_dates(self, dose):
        assert dose.date_effective == datetime.datetime(2022, 1, 6)
        assert dose.date_waning == datetime.datetime(2022, 1, 8)
        assert dose.date_finished == datetime.datetime(2022, 1, 18)

    def test_time_evolution(self, dose):
        assert (
            dose.get_efficacy(
                date=datetime.datetime(2022, 1, 1),
                infection_id=delta_id,
                protection_type="infection",
            )
            == 0.1
        )
        assert (
            dose.get_efficacy(
                date=datetime.datetime(2022, 1, 2),
                infection_id=delta_id,
                protection_type="infection",
            )
            == (0.9 - 0.1) / 5 + 0.1
        )
        assert (
            dose.get_efficacy(
                date=datetime.datetime(2022, 1, 9),
                infection_id=delta_id,
                protection_type="infection",
            )
            == (0.45 - 0.9) / 10 + 0.9
        )
        assert (
            dose.get_efficacy(
                date=datetime.datetime(2022, 1, 20),
                infection_id=delta_id,
                protection_type="infection",
            )
            == 0.45
        )


@pytest.fixture(name="trajectory")
def make_trajectory():
    prior_efficacy = Efficacy(
        infection={delta_id: 0.1, omicron_id: 0.1},
        symptoms={delta_id: 0.1, omicron_id: 0.1},
        waning_factor=1.0,
    )
    first_dose_efficacy = Efficacy(
        infection={delta_id: 0.3, omicron_id: 0.3},
        symptoms={delta_id: 0.3, omicron_id: 0.3},
        waning_factor=0.5,
    )
    first_dose = Dose(
        number=0,
        days_administered_to_effective=5,
        days_effective_to_waning=2,
        days_waning=10,
        efficacy=first_dose_efficacy,
        prior_efficacy=prior_efficacy,
        date_administered=datetime.datetime(2022, 1, 1),
    )
    second_dose_efficacy = Efficacy(
        infection={delta_id: 0.9, omicron_id: 0.9},
        symptoms={delta_id: 0.9, omicron_id: 0.9},
        waning_factor=0.5,
    )
    first_dose_efficacy_waned = Efficacy(
        infection={delta_id: 0.15, omicron_id: 0.15},
        symptoms={delta_id: 0.15, omicron_id: 0.15},
        waning_factor=1.0,
    )

    second_dose = Dose(
        number=1,
        days_administered_to_effective=5,
        days_effective_to_waning=2,
        days_waning=10,
        efficacy=second_dose_efficacy,
        prior_efficacy=first_dose_efficacy_waned,
        date_administered=datetime.datetime(2022, 3, 1),
    )
    return VaccineTrajectory(doses=[first_dose, second_dose])


class TestVaccineTrajectory:
    def test_dose_index(self, trajectory):
        assert trajectory.get_dose_index(date=datetime.datetime(2022, 1, 1)) == 0
        assert trajectory.get_dose_index(date=datetime.datetime(2022, 1, 8)) == 0
        assert trajectory.get_dose_index(date=datetime.datetime(2022, 3, 1)) == 1
        assert trajectory.get_dose_index(date=datetime.datetime(2022, 3, 20)) == 1

    def test_dose_number(self, trajectory):
        assert trajectory.get_dose_number(date=datetime.datetime(2022, 1, 1)) == 0
        assert trajectory.get_dose_number(date=datetime.datetime(2022, 3, 20)) == 1

    def test_time_evolution(self, trajectory):
        n_days = 500
        for days in range(n_days):
            date = trajectory.first_dose_date + datetime.timedelta(days=days)
            trajectory.update_trajectory_stage(date=date)
            if date==datetime.datetime(2022, 1, 1):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 1),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.1
                )
            elif date==datetime.datetime(2022, 1, 2):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 2),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == (0.3 - 0.1) / 5 + 0.1
                )
            elif date==datetime.datetime(2022, 1, 6):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 6),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.3)
                )
            elif date==datetime.datetime(2022, 1, 7):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 7),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.3)
                )
            elif date==datetime.datetime(2022, 1, 8):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 8),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.3)
                )
            elif date==datetime.datetime(2022, 1, 9):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 9),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx((0.15 - 0.3) / 10 + 0.3)
                )
            elif date==datetime.datetime(2022, 1, 19):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 19),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.15
                )

            elif date==datetime.datetime(2022, 3, 2):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 2),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == (0.9 - 0.15) / 5 + 0.15
                )
            elif date==datetime.datetime(2022, 3, 6):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 6),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.9)
                )
            elif date==datetime.datetime(2022, 3, 7):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 7),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.9)
                )

            elif date==datetime.datetime(2022, 3, 8):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 8),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.9)
                )
            elif date==datetime.datetime(2022, 3, 9):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 9),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx((0.45 - 0.9) / 10 + 0.9)
                )
            elif date==datetime.datetime(2022, 3, 19):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 19),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.45
                )
            elif date==datetime.datetime(2022, 8, 1):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 8, 1),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.45
                )

@pytest.fixture(name="vaccine")
def make_vaccine():
    effectiveness = [
        {"Delta": {"0-50": 0.6, "50-100": 0.7}},
        {"Delta": {"0-50": 0.8, "50-100": 0.9}},
        {"Delta": {"0-50": 0.9, "50-100": 0.99}},
    ]
    return Vaccine(
        "Pfizer",
        days_administered_to_effective=[0, 10, 5],
        days_effective_to_waning=[2, 2, 2],
        days_waning=[5, 5, 5],
        sterilisation_efficacies=effectiveness,
        symptomatic_efficacies=effectiveness,
        waning_factor=0.5,
    )


class TestVaccine:
    def test__infection_ids(self, vaccine):
        assert set(vaccine.infection_ids) == set([delta_id])

    def test__vt_generation(self, vaccine):
        young_person = Person.from_attributes(age=20)
        old_person = Person.from_attributes(age=70)
        vts = []
        for person in [young_person, old_person]:
            person.immunity.susceptibility_dict = {delta_id: 1.0, omicron_id: 1.0}
            person.immunity.effective_multiplier_dict = {delta_id: 1.0, omicron_id: 1.0}
            vts.append(
                vaccine.generate_trajectory(
                    person=person,
                    dose_numbers=[2],
                    date=datetime.datetime(2022, 1, 1),
                    days_to_next_dose=[0],
                )
            )
        for vt in vts:
            assert vt.doses[0].date_administered == datetime.datetime(2022, 1, 1)
            assert len(vt.doses) == 1
            assert vt.doses[0].number == 2
        assert vts[0].doses[0].efficacy.symptoms[delta_id] == 0.9
        assert vts[1].doses[0].efficacy.symptoms[delta_id] == 0.99

    def test__vt_generation_time_evolution(
        self,
    ):
        effectiveness = [
            {"Delta": {"0-100": 0.3}, "Omicron": {"0-100": 0.3}},
            {"Delta": {"0-100": 0.9}, "Omicron": {"0-100": 0.9}},
        ]
        vaccine = Vaccine(
            "Pfizer",
            days_administered_to_effective=[5, 5, 5],
            days_effective_to_waning=[2, 2, 2],
            days_waning=[10, 10, 10],
            sterilisation_efficacies=effectiveness,
            symptomatic_efficacies=effectiveness,
            waning_factor=0.5,
        )

        person = Person.from_attributes(age=20)
        person.immunity.susceptibility_dict = {delta_id: 0.9, omicron_id: 0.9}
        person.immunity.effective_multiplier_dict = {delta_id: 0.9, omicron_id: 0.9}
        trajectory = vaccine.generate_trajectory(
            person=person,
            days_to_next_dose=[0, 59],
            dose_numbers=[0, 1],
            date=datetime.datetime(2022, 1, 1),
        )
        assert trajectory.doses[0].date_administered == datetime.datetime(2022, 1, 1)
        assert trajectory.doses[1].date_administered == datetime.datetime(2022, 3, 1)
        assert len(trajectory.doses) == 2

        n_days = 500
        for days in range(n_days):
            date = trajectory.first_dose_date + datetime.timedelta(days=days)
            trajectory.update_trajectory_stage(date=date)
            if date==datetime.datetime(2022, 1, 1):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 1),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.1)
                )
            elif date==datetime.datetime(2022, 1, 2):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 2),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx((0.3 - 0.1) / 5 + 0.1)
                )
            elif date==datetime.datetime(2022, 1, 6):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 6),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.3)
                )
            elif date==datetime.datetime(2022, 1, 7):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 7),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.3)
                )
            elif date==datetime.datetime(2022, 1, 8):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 8),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.3)
                )
            elif date==datetime.datetime(2022, 1, 9):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 9),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx((0.15 - 0.3) / 10 + 0.3)
                )
            elif date==datetime.datetime(2022, 1, 19):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 1, 19),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.15
                )

            elif date==datetime.datetime(2022, 3, 2):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 2),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == (0.9 - 0.15) / 5 + 0.15
                )
            elif date==datetime.datetime(2022, 3, 6):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 6),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.9)
                )
            elif date==datetime.datetime(2022, 3, 7):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 7),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.9)
                )

            elif date==datetime.datetime(2022, 3, 8):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 8),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx(0.9)
                )
            elif date==datetime.datetime(2022, 3, 9):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 9),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == pytest.approx((0.45 - 0.9) / 10 + 0.9)
                )
            elif date==datetime.datetime(2022, 3, 19):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 3, 19),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.45
                )
            elif date==datetime.datetime(2022, 8, 1):
                assert (
                    trajectory.get_efficacy(
                        date=datetime.datetime(2022, 8, 1),
                        infection_id=delta_id,
                        protection_type="infection",
                    )
                    == 0.45
                )


