import datetime
import pytest
import numpy as np

from june.groups import CareHome
from june.demography import Person, Population

from june.epidemiology.vaccines.vaccines import Vaccine, Vaccines, VaccineTrajectory
from june.epidemiology.vaccines.vaccination_campaign import (
    VaccinationCampaign,
    VaccinationCampaigns,
)
from june.epidemiology.infection.infection import Delta, Omicron
from june.records import Record, RecordReader

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()


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
        waning_factor=1.0,
    )


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
        assert campaign.is_active(datetime.datetime(2022, 1, 2)) == True
        assert campaign.is_active(datetime.datetime(2022, 1, 12)) == False

    def test__is_target_group(self, vaccine):
        young_person = Person(age=5, sex="f")
        old_person = Person(age=51, sex="m")
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="50-100",
        )
        assert campaign.is_target_group(person=young_person) == False
        assert campaign.is_target_group(person=old_person) == True

        campaign = make_campaign(
            vaccine=vaccine,
            group_by="sex",
            group_type="m",
        )
        assert campaign.is_target_group(person=young_person) == False
        assert campaign.is_target_group(person=old_person) == True

    def test__should_be_vaccinated(self, vaccine):
        person = Person(age=5, sex="f")
        campaign = make_campaign(
            vaccine=vaccine, group_by="age", group_type="50-100", dose_numbers=[0, 1]
        )
        person.vaccinated = None
        assert campaign.has_right_dosage(person=person) == True
        person.vaccinated = 1
        assert campaign.has_right_dosage(person=person) == False
        person.vaccinated = 0
        assert campaign.has_right_dosage(person=person) == False

    def test__should_be_vaccinated_booster(self, vaccine):
        person = Person(age=5, sex="f")
        campaign = make_campaign(
            vaccine=vaccine, group_by="age", group_type="50-100", dose_numbers=[2]
        )
        person.vaccinated = None
        assert campaign.has_right_dosage(person=person) == False

        person.vaccinated = 1
        assert campaign.has_right_dosage(person=person) == True
        person.vaccinated = 0
        assert campaign.has_right_dosage(person=person) == False

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
        assert campaign.has_right_dosage(person=person) == False
        person.vaccine_type = "Pfizer"
        assert campaign.has_right_dosage(person=person) == True
        person.vaccine_type = "Other"
        assert campaign.has_right_dosage(person=person) == False


class TestCampaign:
    def test__daily_prob(self, vaccine):
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="0-100",
        )
        campaign.group_coverage = 0.3
        total_days = 10
        assert campaign.daily_vaccine_probability(days_passed=5) == 0.3 * (
            1.0 / (total_days - 5 * 0.3)
        )

    def test__vaccinate(self, vaccine):
        person = Person.from_attributes(age=5, sex="f")
        person.immunity.susceptibility_dict = {delta_id: 0.9, omicron_id: 0.9}
        person.immunity.effective_multiplier_dict = {delta_id: 0.9, omicron_id: 0.9}
 
        date=datetime.datetime(2022,1,1)
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="0-100",
        )
        campaign.vaccinate(person,date=date,)
        assert isinstance(person.vaccine_trajectory, VaccineTrajectory)
        assert person.vaccine_trajectory.doses[0].date_administered == date
        assert person.id in campaign.vaccinated_ids


    def test__update_vaccine_effect(self, vaccine):
        person = Person.from_attributes(age=5, sex="f")
        person.immunity.susceptibility_dict = {delta_id: 0.9, omicron_id: 0.9}
        person.immunity.effective_multiplier_dict = {delta_id: 0.9, omicron_id: 0.9}
 
        date=datetime.datetime(2022,1,1)
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="0-100",
        )
        campaign.vaccinate(person,date=date,)
        n_days = 200
        trajectory = person.vaccine_trajectory
        for days in range(n_days):
            date = trajectory.first_dose_date + datetime.timedelta(days=days)
            campaign.update_vaccine_effect(person=person,date=date)
        assert person.immunity.susceptibility_dict[delta_id] == pytest.approx(0.2)
        assert person.immunity.effective_multiplier_dict[delta_id] == pytest.approx(0.2)

    def test__update_vaccine_effect_high_initial_immunity(self, vaccine):
        person = Person.from_attributes(age=5, sex="f")
        person.immunity.susceptibility_dict = {delta_id: 0.1, omicron_id: 0.1}
        person.immunity.effective_multiplier_dict = {delta_id: 0.1, omicron_id: 0.1}
 
        date=datetime.datetime(2022,1,1)
        campaign = make_campaign(
            vaccine=vaccine,
            group_by="age",
            group_type="0-100",
        )
        campaign.vaccinate(person,date=date,)
        n_days = 200
        trajectory = person.vaccine_trajectory
        for days in range(n_days):
            date = trajectory.first_dose_date + datetime.timedelta(days=days)
            campaign.update_vaccine_effect(person=person,date=date)
        assert person.immunity.susceptibility_dict[delta_id] == pytest.approx(0.1)
        assert person.immunity.effective_multiplier_dict[delta_id] == pytest.approx(0.1)

