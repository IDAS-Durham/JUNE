import datetime
import pytest
import numpy as np

from june.demography import Person, Population

from june.epidemiology.vaccines.vaccines import Vaccine, VaccineTrajectory
from june.epidemiology.vaccines.vaccination_campaign import (
    VaccinationCampaign,
    VaccinationCampaigns,
)
from june.epidemiology.infection.infection import Delta, Omicron
from june.records import Record, RecordReader

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()


@pytest.fixture(name="effectiveness")
def make_effectiveness():
    return [
        {"Delta": {"0-50": 0.6, "50-100": 0.7}},
        {"Delta": {"0-50": 0.8, "50-100": 0.9}},
        {"Delta": {"0-50": 0.9, "50-100": 0.99}},
    ]


@pytest.fixture(name="vaccine")
def make_vaccine(effectiveness):
    return Vaccine(
        "Pfizer",
        days_administered_to_effective=[0, 10, 5],
        days_effective_to_waning=[2, 2, 2],
        days_waning=[5, 5, 5],
        sterilisation_efficacies=effectiveness,
        symptomatic_efficacies=effectiveness,
        waning_factor=1.0,
    )


@pytest.fixture(name="fast_population")
def make_fast_population():
    people = []
    for age in range(100):
        for _ in range(10):
            person = Person.from_attributes(age=age)
            people.append(person)
    return Population(people)


def make_campaign(
    vaccine, group_by, group_type, dose_numbers=[0, 1], last_dose_type=None
):
    days_to_next_dose = [0, 20, 20, 20]
    return VaccinationCampaign(
        vaccine=vaccine,
        days_to_next_dose=[
            days_to_next_dose[dose_number] for dose_number in dose_numbers
        ],
        dose_numbers=dose_numbers,
        start_time="2022-01-01",
        end_time="2022-01-11",
        group_by=group_by,
        group_type=group_type,
        group_coverage=1.0,
        last_dose_type=last_dose_type,
    )


class TestWhenWho:
    def test__is_active(self, vaccine):
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="50-100",
        )
        assert campaign.is_active(datetime.datetime(2022, 1, 2)) is True
        assert campaign.is_active(datetime.datetime(2022, 1, 12)) is False

    def test__is_target_group(self, vaccine):
        young_person = Person(age=5, sex="f")
        old_person = Person(age=51, sex="m")
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="50-100",
        )
        assert campaign.is_target_group(person=young_person) is False
        assert campaign.is_target_group(person=old_person) is True

        campaign = make_campaign(
            vaccine=vaccine,
            group_by="sex",
            group_type="m",
        )
        assert campaign.is_target_group(person=young_person) is False
        assert campaign.is_target_group(person=old_person) is True

    def test__should_be_vaccinated(self, vaccine):
        person = Person(age=5, sex="f")
        campaign = make_campaign(
            vaccine=vaccine, group_by="age", group_type="50-100", dose_numbers=[0, 1]
        )
        person.vaccinated = None
        assert campaign.has_right_dosage(person=person) is True
        person.vaccinated = 1
        assert campaign.has_right_dosage(person=person) is False
        person.vaccinated = 0
        assert campaign.has_right_dosage(person=person) is False

    def test__should_be_vaccinated_booster(self, vaccine):
        person = Person(age=5, sex="f")
        campaign = make_campaign(
            vaccine=vaccine, group_by="age", group_type="50-100", dose_numbers=[2]
        )
        person.vaccinated = None
        assert campaign.has_right_dosage(person=person) is False

        person.vaccinated = 1
        assert campaign.has_right_dosage(person=person) is True
        person.vaccinated = 0
        assert campaign.has_right_dosage(person=person) is False

    def test__should_be_vaccinated_last_dose(self, vaccine):
        person = Person(age=5, sex="f")
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="50-100",
            dose_numbers=[2],
            last_dose_type=["Pfizer"],
        )
        person.vaccinated = 1
        person.vaccine_type = None
        assert campaign.has_right_dosage(person=person) is False
        person.vaccine_type = "Pfizer"
        assert campaign.has_right_dosage(person=person) is True
        person.vaccine_type = "Other"
        assert campaign.has_right_dosage(person=person) is False


class TestCampaign:
    def test__daily_prob(self, vaccine):
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="0-100",
        )
        campaign.group_coverage = 0.3
        total_days = 10
        assert campaign.daily_vaccination_probability(days_passed=5) == 0.3 * (
            1.0 / (total_days - 5 * 0.3)
        )

    def test__vaccinate(self, vaccine):
        person = Person.from_attributes(age=5, sex="f")
        person.immunity.susceptibility_dict = {delta_id: 0.9, omicron_id: 0.9}
        person.immunity.effective_multiplier_dict = {delta_id: 0.9, omicron_id: 0.9}

        date = datetime.datetime(2022, 1, 1)
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="0-100",
        )
        campaign.vaccinate(
            person,
            date=date,
        )
        assert isinstance(person.vaccine_trajectory, VaccineTrajectory)
        assert person.vaccine_trajectory.doses[0].date_administered == date
        assert person.id in campaign.vaccinated_ids


class TestCampaigns:
    def test__apply(self, fast_population, effectiveness):
        pfizer = Vaccine(
            "Pfizer",
            days_administered_to_effective=[0, 10, 5],
            days_effective_to_waning=[2, 2, 2],
            days_waning=[5, 5, 5],
            sterilisation_efficacies=effectiveness,
            symptomatic_efficacies=effectiveness,
            waning_factor=1.0,
        )

        az = Vaccine(
            "AstraZeneca",
            days_administered_to_effective=[0, 10, 5],
            days_effective_to_waning=[2, 2, 2],
            days_waning=[5, 5, 5],
            sterilisation_efficacies=effectiveness,
            symptomatic_efficacies=effectiveness,
            waning_factor=1.0,
        )
        pfizer_campaign = VaccinationCampaign(
            vaccine=pfizer,
            days_to_next_dose=[0, 10],
            dose_numbers=[0, 1],
            start_time="2022-01-01",
            end_time="2022-01-11",
            group_by="age",
            group_type="0-50",
            group_coverage=0.6,
        )
        az_campaign = VaccinationCampaign(
            vaccine=az,
            days_to_next_dose=[0, 10],
            dose_numbers=[0, 1],
            start_time="2022-01-01",
            end_time="2022-01-11",
            group_by="age",
            group_type="0-50",
            group_coverage=0.1,
        )
        campaigns = VaccinationCampaigns([pfizer_campaign, az_campaign])
        start_date = datetime.datetime(2021, 12, 31)
        n_days = 11
        for days in range(n_days):
            date = start_date + datetime.timedelta(days=days)
            for person in fast_population:
                campaigns.apply(person=person, date=date)

        n_pfizer, n_az = 0, 0
        for person in fast_population:
            if person.vaccine_type == "Pfizer":
                n_pfizer += 1
            elif person.vaccine_type == "AstraZeneca":
                n_az += 1
        assert 0.6 * 0.5 * len(fast_population) == pytest.approx(n_pfizer, rel=0.1)
        assert 0.1 * 0.5 * len(fast_population) == pytest.approx(n_az, rel=0.15)


@pytest.fixture(name="population")
def make_population():
    people = []
    for age in range(100):
        for _ in range(100):
            person = Person.from_attributes(age=age)
            people.append(person)
    return Population(people)


@pytest.fixture(name="vax_campaigns")
def make_campaigns():
    ster_effectiveness = [
        {"Delta": {"0-100": 0.3}, "Omicron": {"0-100": 0.2}},
        {"Delta": {"0-100": 0.7}, "Omicron": {"0-100": 0.2}},
        {"Delta": {"0-100": 0.9}, "Omicron": {"0-100": 0.8}},
    ]
    sympto_effectiveness = [
        {"Delta": {"0-100": 0.3}, "Omicron": {"0-100": 0.5}},
        {"Delta": {"0-100": 0.7}, "Omicron": {"0-100": 0.2}},
        {"Delta": {"0-100": 0.7}, "Omicron": {"0-100": 0.1}},
    ]

    vaccine = Vaccine(
        "Test",
        days_administered_to_effective=[1, 2, 10],
        days_effective_to_waning=[0, 0, 0],
        days_waning=[0, 0, 0],
        sterilisation_efficacies=ster_effectiveness,
        symptomatic_efficacies=sympto_effectiveness,
        waning_factor=1.0,
    )
    return VaccinationCampaigns(
        [
            VaccinationCampaign(
                vaccine=vaccine,
                days_to_next_dose=[0, 9, 16],
                start_time="2021-03-01",
                end_time="2021-03-05",
                group_by="age",
                group_type="20-40",
                group_coverage=0.6,
                dose_numbers=[0, 1, 2],
            )
        ]
    )


class TestVaccinationInitialization:
    def test__to_finished(
        self,
        vax_campaigns,
    ):
        assert (
            vax_campaigns.vaccination_campaigns[0].days_from_administered_to_finished
            == 38
        )

    def test__vaccination_from_the_past(
        self,
        population,
        vax_campaigns,
    ):
        date = datetime.datetime(2021, 4, 30)
        vax_campaigns.apply_past_campaigns(
            people=population,
            date=date,
        )
        n_vaccinated = 0
        for person in population:
            if (person.age < 20) or (person.age >= 40):
                assert person.vaccinated is None
            else:
                if person.vaccinated is not None:
                    n_vaccinated += 1
                    assert np.isclose(
                        person.immunity.susceptibility_dict[delta_id], 0.1
                    )
                    assert np.isclose(
                        person.immunity.susceptibility_dict[omicron_id], 0.2
                    )
                    assert np.isclose(
                        person.immunity.effective_multiplier_dict[delta_id],
                        0.3,
                    )
                    assert np.isclose(
                        person.immunity.effective_multiplier_dict[omicron_id],
                        0.9,
                    )
        assert np.isclose(n_vaccinated, 60 * 20, atol=0, rtol=0.1)

    def test__record_saving(
        self,
        fast_population,
        vax_campaigns,
    ):
        record = Record(record_path="results")
        dates = vax_campaigns.collect_all_dates_in_past(
            current_date=datetime.datetime(2021, 5, 1),
        )
        assert len(set(dates)) == len(dates)
        vax_campaigns.apply_past_campaigns(
            people=fast_population,
            date=datetime.datetime(2021, 5, 1),
            record=record,
        )
        n_vaccinated = 0
        for person in fast_population:
            if person.vaccinated is not None:
                n_vaccinated += 1
        read = RecordReader(results_path="results")
        vaccines_df = read.table_to_df("vaccines", "vaccinated_ids")
        first_dose_df = vaccines_df[vaccines_df["dose_numbers"] == 0]
        second_dose_df = vaccines_df[vaccines_df["dose_numbers"] == 1]
        third_dose_df = vaccines_df[vaccines_df["dose_numbers"] == 2]
        assert len(first_dose_df) == n_vaccinated
        assert len(third_dose_df) == n_vaccinated
        assert len(first_dose_df) == len(second_dose_df)
