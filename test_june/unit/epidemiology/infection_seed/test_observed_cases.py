import yaml
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from june.epidemiology.infection_seed import Observed2Cases
from june.demography import Person
from june.geography import Area, SuperArea, SuperAreas
from june.epidemiology.infection.trajectory_maker import TrajectoryMaker
from june import paths


@pytest.fixture(name="oc")
def get_oc(health_index_generator):
    area_super_region_df = pd.DataFrame(
        {
            "area": ["beautiful"],
            "super_area": ["marvellous"],
            "region": ["magnificient"],
        }
    )
    area_super_region_df.set_index("area", inplace=True)
    age_per_area_dict = {str(i): 0 for i in range(101)}
    age_per_area_dict["50"] = 1
    age_per_area_df = pd.DataFrame(age_per_area_dict, index=["beautiful"])
    female_fraction_per_area_dict = {str(i): 0 for i in range(0, 101, 5)}
    female_fraction_per_area_dict["50"] = 1.0
    female_fraction_per_area_df = pd.DataFrame(
        female_fraction_per_area_dict, index=["beautiful"]
    )
    with open(
        paths.configs_path
        / "defaults/epidemiology/infection/symptoms/trajectories.yaml"
    ) as f:
        trajectories = yaml.safe_load(f)["trajectories"]
    symptoms_trajectories = [
        TrajectoryMaker.from_dict(trajectory) for trajectory in trajectories
    ]
    return Observed2Cases(
        age_per_area_df=age_per_area_df,
        female_fraction_per_area_df=female_fraction_per_area_df,
        area_super_region_df=area_super_region_df,
        health_index_generator=health_index_generator,
        symptoms_trajectories=symptoms_trajectories,
    )


@pytest.fixture(name="oc_multiple_super_areas")
def get_oc_multiple_super_areas(health_index_generator):
    area_super_region_df = pd.DataFrame(
        {
            "area": ["area_1", "area_2", "area_3"],
            "super_area": ["super_1", "super_2", "super_3"],
            "region": ["magnificient", "magnificient", "magnificient"],
        }
    )
    area_super_region_df.set_index("area", inplace=True)
    age_per_area_dict = {str(i): [0, 0, 0] for i in range(101)}
    age_per_area_dict["50"] = [1, 1, 1]
    age_per_area_df = pd.DataFrame(
        age_per_area_dict, index=["area_1", "area_2", "area_3"]
    )
    female_fraction_per_area_dict = {str(i): [0, 0, 0] for i in range(0, 101, 5)}
    female_fraction_per_area_dict["50"] = [1, 1, 1]
    female_fraction_per_area_df = pd.DataFrame(
        female_fraction_per_area_dict, index=["area_1", "area_2", "area_3"]
    )
    return Observed2Cases(
        age_per_area_df=age_per_area_df,
        female_fraction_per_area_df=female_fraction_per_area_df,
        area_super_region_df=area_super_region_df,
        health_index_generator=health_index_generator,
        regional_infections_per_hundred_thousand=2.0e8,
    )


def test__generate_demography_dfs_by_region(oc):
    assert oc.females_per_age_region_df.loc["magnificient"]["50"] == 1
    assert oc.females_per_age_region_df.loc["magnificient"].sum() == 1
    assert oc.males_per_age_region_df.loc["magnificient"].sum() == 0


def test__avg_rates_by_age_and_sex(oc):
    rates_dict = oc.get_symptoms_rates_per_age_sex()
    assert list(rates_dict.keys()) == ["m", "f"]
    np.testing.assert_equal(np.array(list(rates_dict["f"].keys())), np.arange(100))
    np.testing.assert_equal(np.array(list(rates_dict["m"].keys())), np.arange(100))
    assert rates_dict["f"][0].shape[0] == 8
    avg_death_rate = oc.weight_rates_by_age_sex_per_region(
        rates_dict, symptoms_tags=("dead_home", "dead_hospital", "dead_icu")
    )
    np.testing.assert_equal(
        avg_death_rate["magnificient"],
        np.array(
            np.diff(
                oc.health_index_generator(Person(age=50, sex="f"), infection_id=0),
                prepend=0.0,
                append=1.0,
            )
        )[[5, 6, 7]],
    )


def test__expected_cases(oc):
    n_cases = oc.get_latent_cases_from_observed(
        n_observed=20, avg_rates=[0.2, 0.1, 0.1]
    )
    assert n_cases == 20 / 0.4


def test__latent_cases_per_region(oc):
    n_observed_df = pd.DataFrame(
        {
            "date": ["2020-04-20", "2020-04-21"],
            "magnificient": [100, 200],
        }
    )
    n_observed_df.set_index("date", inplace=True)
    n_observed_df.index = pd.to_datetime(n_observed_df.index)
    n_expected_true_df = pd.DataFrame(
        {
            "date": ["2020-04-10", "2020-04-11"],
            "magnificient": [100 / 0.4, 200 / 0.4],
        }
    )
    n_expected_true_df.set_index("date", inplace=True)
    n_expected_true_df.index = pd.to_datetime(n_expected_true_df.index)
    avg_death_rate = {"magnificient": [0.2, 0.1, 0.1]}
    n_expected_df = oc.get_latent_cases_per_region(n_observed_df, 10, avg_death_rate)
    pd.testing.assert_frame_equal(n_expected_df, n_expected_true_df)


def test__filter_trajectories(oc):
    hospitalised_trajectories = oc.filter_symptoms_trajectories(
        oc.symptoms_trajectories, symptoms_to_keep=["hospitalised"]
    )
    for trajectory in hospitalised_trajectories:
        symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
        assert "hospitalised" in symptom_tags

    dead_trajectories = oc.filter_symptoms_trajectories(
        oc.symptoms_trajectories, symptoms_to_keep=["dead_hospital", "dead_icu"]
    )
    for trajectory in dead_trajectories:
        symptom_tags = [stage.symptoms_tag.name for stage in trajectory.stages]
        assert "dead" in symptom_tags[-1]


def test__median_completion_time(oc):
    assert oc.get_median_completion_time(oc.symptoms_trajectories[0].stages[1]) == 14


def test__get_time_it_takes_to_symptoms(oc):
    asymptomatic_trajectories = oc.filter_symptoms_trajectories(
        oc.symptoms_trajectories, symptoms_to_keep=["asymptomatic"]
    )
    assert (
        2.0
        < oc.get_time_it_takes_to_symptoms(asymptomatic_trajectories, ["asymptomatic"])[
            0
        ]
        < 5.0
    )

    hospitalised_trajectories = oc.filter_symptoms_trajectories(
        oc.symptoms_trajectories, symptoms_to_keep=["hospitalised", "intensive_care"]
    )
    assert len(hospitalised_trajectories) == 4
    times_to_hospital = oc.get_time_it_takes_to_symptoms(
        hospitalised_trajectories, ["hospitalised", "intensive_care"]
    )
    for time in times_to_hospital:
        assert 1.0 < time < 16.0


def test__get_weighted_time_to_symptoms(oc):
    rates_dict = oc.get_symptoms_rates_per_age_sex()
    avg_rates = oc.weight_rates_by_age_sex_per_region(
        rates_dict,
        symptoms_tags=["hospitalised", "intensive_care", "dead_hospital", "dead_icu"],
    )
    avg_rates = avg_rates["magnificient"]
    hospitalised_trajectories = oc.filter_symptoms_trajectories(
        oc.symptoms_trajectories,
        symptoms_to_keep=[
            "hospitalised",
            "intensive_care",
            "dead_hospital",
            "dead_icu",
        ],
    )

    avg_time_to_hospital = oc.get_weighted_time_to_symptoms(
        hospitalised_trajectories, avg_rates, ["hospitalised", "intensive_care"]
    )
    assert 1.0 < avg_time_to_hospital < 13.0


def test__cases_from_observation_per_super_area(oc_multiple_super_areas):
    n_observed_df = pd.DataFrame(
        {
            "date": ["2020-04-20", "2020-04-21"],
            "magnificient": [100, 200],
        }
    )
    n_observed_df.set_index("date", inplace=True)
    n_observed_df.index = pd.to_datetime(n_observed_df.index)
    n_expected_true_df = pd.DataFrame(
        {
            "date": ["2020-04-10", "2020-04-11"],
            "super_1": [round(100 / 3 / 0.4), round(200 / 3 / 0.4)],
            "super_2": [round(100 / 3 / 0.4), round(200 / 3 / 0.4)],
            "super_3": [round(100 / 3 / 0.4), round(200 / 3 / 0.4)],
        }
    )
    n_expected_true_df.set_index("date", inplace=True)
    n_expected_true_df.index = pd.to_datetime(n_expected_true_df.index)
    avg_death_rate = {"magnificient": [0.2, 0.1, 0.1]}
    n_expected_per_region_df = oc_multiple_super_areas.get_latent_cases_per_region(
        n_observed_df, 10, avg_death_rate
    )
    super_area_weights = oc_multiple_super_areas.get_super_area_population_weights()

    assert (
        super_area_weights.groupby("region").sum()["weights"].loc["magnificient"] == 1.0
    )
    assert super_area_weights.loc["super_1"]["weights"] == pytest.approx(0.33, rel=0.05)
    assert super_area_weights.loc["super_2"]["weights"] == pytest.approx(0.33, rel=0.05)
    assert super_area_weights.loc["super_3"]["weights"] == pytest.approx(0.33, rel=0.05)
    n_expected_per_super_area_df = (
        oc_multiple_super_areas.convert_regional_cases_to_super_area(
            n_expected_per_region_df,
            starting_date="2020-04-10",
        )
    )

    pd.testing.assert_series_equal(
        n_expected_per_super_area_df.sum(axis=1),
        n_expected_per_region_df["magnificient"].astype(int),
        check_names=False,
    )
