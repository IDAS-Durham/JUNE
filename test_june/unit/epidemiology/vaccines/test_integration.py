import datetime
import pytest
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.vaccines.vaccines import Vaccine
from june.epidemiology.vaccines.vaccination_campaign import (
    VaccinationCampaign,
    VaccinationCampaigns,
)
from june.demography import Person, Population
from june.world import World
from june.epidemiology.infection.infection import Delta, Omicron

delta_id = Delta.infection_id()
omicron_id = Omicron.infection_id()


@pytest.fixture(name="dates_values")
def make_dates_and_values():
    return {
        datetime.datetime(2022, 1, 1): 0.1,
        datetime.datetime(2022, 1, 2): (0.3 - 0.1) / 5 + 0.1,
        datetime.datetime(2022, 1, 6): 0.3,
        datetime.datetime(2022, 1, 7): 0.3,
        datetime.datetime(2022, 1, 8): 0.3,
        datetime.datetime(2022, 1, 9): (0.15 - 0.3) / 10 + 0.3,
        datetime.datetime(2022, 1, 19): 0.15,
        datetime.datetime(2022, 3, 2): (0.9 - 0.15) / 5 + 0.15,
        datetime.datetime(2022, 3, 6): 0.9,
        datetime.datetime(2022, 3, 7): 0.9,
        datetime.datetime(2022, 3, 8): 0.9,
        datetime.datetime(2022, 3, 9): (0.45 - 0.9) / 10 + 0.9,
        datetime.datetime(2022, 3, 19): 0.45,
        datetime.datetime(2022, 8, 1): 0.45,
    }


@pytest.fixture(name="vaccine")
def make_vaccine():
    effectiveness = [
        {"Delta": {"0-100": 0.3}, "Omicron": {"0-100": 0.3}},
        {"Delta": {"0-100": 0.9}, "Omicron": {"0-100": 0.9}},
    ]
    return Vaccine(
        "Pfizer",
        days_administered_to_effective=[5, 5, 5],
        days_effective_to_waning=[2, 2, 2],
        days_waning=[10, 10, 10],
        sterilisation_efficacies=effectiveness,
        symptomatic_efficacies=effectiveness,
        waning_factor=0.5,
    )


@pytest.fixture(name="vaccination_campaigns")
def make_campaigns(vaccine):
    days_to_next_dose = [0, 59]
    dose_numbers = [0, 1]
    vc = VaccinationCampaign(
        vaccine=vaccine,
        days_to_next_dose=[
            days_to_next_dose[dose_number] for dose_number in dose_numbers
        ],
        dose_numbers=dose_numbers,
        start_time="2022-01-01",
        end_time="2022-01-11",
        group_by="age",
        group_type="0-100",
        group_coverage=1.0,
    )
    return VaccinationCampaigns([vc])


@pytest.fixture(name="vaccine_epidemiology")
def make_epidemiology(selectors, vaccination_campaigns):
    return Epidemiology(
        infection_selectors=selectors, vaccination_campaigns=vaccination_campaigns
    )


@pytest.fixture(name="world")
def make_world():
    world = World()
    person = Person.from_attributes(age=30)
    person.immunity.susceptibility_dict = {delta_id: 0.9, omicron_id: 0.9}
    person.immunity.effective_multiplier_dict = {delta_id: 0.9, omicron_id: 0.9}
    population = Population([person])
    world.people = population
    return world


class TestEpi:
    def test__update_health(self, world, vaccine_epidemiology, dates_values):
        person = world.people[0]

        vc = vaccine_epidemiology.vaccination_campaigns.vaccination_campaigns[0]
        start_date = datetime.datetime(2022, 1, 1)
        vc.vaccinate(person, date=start_date)
        n_days = 500
        for days in range(n_days):
            date = start_date + datetime.timedelta(days)
            vaccine_epidemiology.update_health_status(
                world=world, time=0.0, duration=4, date=date, vaccinate=True
            )
            if date in dates_values:
                assert person.immunity.susceptibility_dict[delta_id] == pytest.approx(
                    1.0 - dates_values[date]
                )
