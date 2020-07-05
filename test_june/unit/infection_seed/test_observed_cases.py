import yaml
import pytest
import pandas as pd
from datetime import datetime
from june.infection_seed import Observed2Cases
from june.demography import Person
from june.demography.geography import Area, SuperArea, SuperAreas
from june.infection import HealthIndexGenerator
from june import paths


@pytest.fixture(name="oc")
def get_oc():
    person = Person.from_attributes(age=90, sex="m")
    area = Area(name='E00003255', super_area='E02000134', coordinates=(0,0))
    area.add(person)
    super_area = SuperArea(areas=[area], coordinates=(1,1), name='E02000134')
    super_areas = SuperAreas([super_area])
    health_index = HealthIndexGenerator.from_file()
    return Observed2Cases.from_file(super_areas=super_areas, health_index=health_index)

def test__find_regions(oc):
    regions = oc.find_regions_for_super_areas(oc.super_areas)
    assert regions == ['London']

def test__filter_trajectories(oc):
    hospitalised_trajectories = oc.filter_trajectories(
        oc.trajectories, symptoms_to_keep=["hospitalised"]
    )
    for trajectory in hospitalised_trajectories:
        symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
        assert "hospitalised" in symptom_tags

    dead_trajectories = oc.filter_trajectories(
        oc.trajectories, symptoms_to_keep=["dead_hospital", "dead_icu"]
    )
    for trajectory in dead_trajectories:
        symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
        assert "dead" in symptom_tags[-1]


def test__mean_completion_time(oc):
    assert oc.get_mean_completion_time(oc.trajectories[0].stages[1]) == 14


def test__get_time_it_takes_to_symptoms(oc):
    asymptomatic_trajectories = oc.filter_trajectories(
        oc.trajectories, symptoms_to_keep=["asymptomatic"]
    )
    assert (
        2.0
        < oc.get_time_it_takes_to_symptoms(asymptomatic_trajectories, ["asymptomatic"])[
            0
        ]
        < 5.0
    )

    hospitalised_trajectories = oc.filter_trajectories(
        oc.trajectories, symptoms_to_keep=["hospitalised", "intensive_care"]
    )
    assert len(hospitalised_trajectories) == 4
    times_to_hospital = oc.get_time_it_takes_to_symptoms(
        hospitalised_trajectories, ["hospitalised", "intensive_care"]
    )
    for time in times_to_hospital:
        assert 8.0 < time < 10.0


def test__get_avg_rate_for_symptoms(oc):
    avg_rates = oc.get_avg_rate_for_symptoms(
        ["hospitalised", "intensive_care", "dead_hospital", "dead_icu"], region='London'
    )
    person_health_index = oc.health_index(oc.population['London'][0])
    assert len(avg_rates) == 4
    assert avg_rates[-1] == 1 - person_health_index[-1]
    assert avg_rates[-2] == person_health_index[-1] - person_health_index[-2]
    assert avg_rates[-3] == person_health_index[-3] - person_health_index[-4]
    assert avg_rates[-4] == person_health_index[-4] - person_health_index[-5]


def test__get_avg_time_to_symptoms(oc):
    avg_rates = oc.get_avg_rate_for_symptoms(
        ["hospitalised", "intensive_care", "dead_hospital", "dead_icu"], region='London'
    )

    hospitalised_trajectories = oc.filter_trajectories(
        oc.trajectories,
        symptoms_to_keep=[
            "hospitalised",
            "intensive_care",
            "dead_hospital",
            "dead_icu",
        ],
    )

    avg_rates = oc.get_avg_rate_for_symptoms(
        ["hospitalised", "intensive_care", "dead_hospital", "dead_icu"], region='London'
    )
    avg_time_to_hospital = oc.get_avg_time_to_symptoms(
        hospitalised_trajectories, avg_rates, ["hospitalised", "intensive_care"]
    )
    assert 8.0 < avg_time_to_hospital < 10.0


def test__n_cases_from_observed(oc):
    assert oc.get_n_cases_from_observed(100, [0.0, 0.4]) == 250

def test__cases_from_observations(oc):
    n_observed_df = pd.DataFrame(
            {
            'date':['2020-04-20','2020-04-21'], 
            'London': [100,200],
             }
        )
    n_observed_df.set_index('date', inplace=True)
    n_observed_df.index = pd.to_datetime(n_observed_df.index)
    cases_df = oc.cases_from_observation(n_observed_df, time_to_get_there=5, avg_rates=[0.4], 
            region='London')
    assert cases_df.index[0] == datetime(2020,4,15) 
    assert cases_df.index[1] == datetime(2020,4,16) 
    assert cases_df['London'].iloc[0] == 250 
    assert cases_df['London'].iloc[1] == 500 


