import datetime
import numpy as np
import json
import pandas as pd
import yaml
import pytest
import dateutil.parser

from tables import open_file
from june import paths
from june.records import Record
from june.groups import Hospital, Hospitals, Household, Households, CareHome, CareHomes
from june.policy import Policies
from june.activity import ActivityManager
from june.demography import Person, Population
from june.interaction import Interaction
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection import InfectionSelector, HealthIndexGenerator
from june.epidemiology.infection_seed import InfectionSeed, InfectionSeeds
from june.geography.geography import (
    Areas,
    SuperAreas,
    Regions,
    Area,
    SuperArea,
    Region,
)
from june.groups import Supergroup
from june import World

config_interaction = paths.configs_path / "tests/interaction.yaml"

@pytest.fixture(name="dummy_world", scope="module")
def create_dummy_world():
    # 2 regions, 2 hospitals, 1 care home 1 household
    regions = Regions([Region(name="region_1"), Region(name="region_2")])
    regions[0].super_areas = [
        SuperArea(name="super_1", coordinates=(0.0, 0.0), region=regions[0]),
        SuperArea(name="super_2", coordinates=(1.0, 1.0), region=regions[0]),
    ]
    regions[1].super_areas = [
        SuperArea(name="super_3", coordinates=(2.0, 2.0), region=regions[1])
    ]
    super_areas = SuperAreas(regions[0].super_areas + regions[1].super_areas)
    super_areas[0].areas = [
        Area(
            name="area_1",
            coordinates=(0.0, 0.0),
            super_area=super_areas[0],
            socioeconomic_index=0.01,
        ),
        Area(
            name="area_2",
            coordinates=(0.0, 0.0),
            super_area=super_areas[0],
            socioeconomic_index=0.02,
        ),
        Area(
            name="area_3",
            coordinates=(0.0, 0.0),
            super_area=super_areas[0],
            socioeconomic_index=0.03,
        ),
    ]
    super_areas[1].areas = [
        Area(
            name="area_4",
            coordinates=(0.0, 0.0),
            super_area=super_areas[1],
            socioeconomic_index=0.11,
        ),
        Area(
            name="area_5",
            coordinates=(0.0, 0.0),
            super_area=super_areas[1],
            socioeconomic_index=0.12,
        ),
    ]
    super_areas[2].areas = [
        Area(
            name="area_6",
            coordinates=(5, 5),
            super_area=super_areas[2],
            socioeconomic_index=0.90,
        )
    ]
    areas = Areas(super_areas[0].areas + super_areas[1].areas + super_areas[2].areas)
    households = Households([Household(area=super_areas[0].areas[0])])
    hospitals = Hospitals(
        [
            Hospital(
                n_beds=1,
                n_icu_beds=1,
                area=areas[5],
                coordinates=(0.0, 0.0),
            )
        ]
    )
    care_homes = CareHomes([CareHome(area=super_areas[0].areas[0])])
    world = World()
    world.areas = areas
    world.super_areas = super_areas
    world.regions = regions
    world.households = households
    world.hospitals = hospitals
    world.care_homes = care_homes
    world.people = [
        Person.from_attributes(id=0, age=0, ethnicity="A"),
        Person.from_attributes(id=1, age=1, ethnicity="B"),
        Person.from_attributes(id=2, age=2, sex="m", ethnicity="C"),
    ]
    world.people[0].area = super_areas[0].areas[0]  # household resident
    world.people[0].subgroups.primary_activity = hospitals[0].subgroups[0]
    world.people[0].subgroups.residence = households[0].subgroups[0]
    world.people[1].area = super_areas[0].areas[0]
    world.people[1].subgroups.residence = households[0].subgroups[0]
    world.people[2].area = super_areas[0].areas[1]  # care home resident
    world.people[2].subgroups.residence = care_homes[0].subgroups[0]
    return world


def test__writing_infections():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 10, 10)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        record.accumulate(
            table_name="infections",
            location_spec="care_home",
            region_name="made_up",
            location_id=0,
            infected_ids=[0, 10, 20],
            infector_ids=[5, 15, 25],
            infection_ids=[0, 0, 0],
        )
        record.events["infections"].record(hdf5_file=record.file, timestamp=timestamp)
        table = record.file.root.infections
        df = pd.DataFrame.from_records(table.read())
    assert len(df) == 3
    assert df.timestamp.unique()[0].decode() == "2020-10-10"
    assert df.location_ids.unique() == [0]
    assert df.region_names.unique() == [b"made_up"]
    assert df.location_specs.unique() == [b"care_home"]
    assert len(df.infected_ids) == 3
    assert df.infected_ids[0] == 0
    assert df.infector_ids[0] == 5
    assert df.infected_ids[1] == 10
    assert df.infector_ids[1] == 15
    assert df.infected_ids[2] == 20
    assert df.infector_ids[2] == 25
    assert df.infection_ids[0] == 0
    assert df.infection_ids[1] == 0
    assert df.infection_ids[2] == 0
    del df


def test__writing_hospital_admissions():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        record.accumulate(
            table_name="hospital_admissions", hospital_id=0, patient_id=10
        )
        record.events["hospital_admissions"].record(
            hdf5_file=record.file, timestamp=timestamp
        )
        table = record.file.root.hospital_admissions
        df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10


def test__writing_hospital_discharges():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        record.accumulate(table_name="discharges", hospital_id=0, patient_id=10)
        record.events["discharges"].record(hdf5_file=record.file, timestamp=timestamp)
        table = record.file.root.discharges
        df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10


def test__writing_intensive_care_admissions():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        record.accumulate(table_name="icu_admissions", hospital_id=0, patient_id=10)
        record.events["icu_admissions"].record(
            hdf5_file=record.file, timestamp=timestamp
        )
        table = record.file.root.icu_admissions
        df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10


def test__writing_death():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        record.accumulate(
            table_name="deaths",
            location_spec="household",
            location_id=0,
            dead_person_id=10,
        )
        record.events["deaths"].record(hdf5_file=record.file, timestamp=timestamp)
        table = record.file.root.deaths
        df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.location_specs.iloc[0].decode() == "household"
    assert df.location_ids.iloc[0] == 0
    assert df.dead_person_ids.iloc[0] == 10


def test__static_people(dummy_world):
    record = Record(
        record_path="results",
        record_static_data=True,
    )
    record.static_data(world=dummy_world)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        table = record.file.root.population
        df = pd.DataFrame.from_records(table.read(), index="id")
    str_cols = record.statics["people"].str_names
    for col in str_cols:
        df[col] = df[col].str.decode("utf-8")
    assert df.loc[0, "age"] == 0
    assert df.loc[1, "age"] == 1
    assert df.loc[2, "age"] == 2
    assert df.loc[0, "primary_activity_type"] == "hospital"
    assert df.loc[0, "primary_activity_id"] == dummy_world.hospitals[0].id
    assert df.loc[1, "primary_activity_type"] == "None"
    assert df.loc[1, "primary_activity_id"] == 0
    assert df.loc[1, "residence_type"] == "household"
    assert df.loc[1, "residence_id"] == dummy_world.households[0].id
    assert df.loc[2, "residence_type"] == "care_home"
    assert df.loc[2, "residence_id"] == dummy_world.care_homes[0].id
    assert df.loc[0, "ethnicity"] == "A"
    assert df.loc[1, "ethnicity"] == "B"
    assert df.loc[2, "ethnicity"] == "C"
    assert df.loc[0, "sex"] == "f"
    assert df.loc[2, "sex"] == "m"

def test__static_with_extras_people(dummy_world):
    record = Record(
        record_path="results",
        record_static_data=True,
    )
    tonto = [0.1,1.3,5.]
    listo = [0.9,0.7,0.]
    vaccine_type = [0,1,2]
    vaccine_name = ['astra','pfizer','moderna']
    record.statics['people'].extra_float_data['tonto'] = tonto
    record.statics['people'].extra_float_data['listo'] = listo  
    record.statics['people'].extra_int_data['vaccine_type'] = vaccine_type
    record.statics['people'].extra_str_data['vaccine_name'] = vaccine_name
    record.static_data(world=dummy_world)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        table = record.file.root.population
        df = pd.DataFrame.from_records(table.read(), index="id")
    str_cols = record.statics["people"].str_names
    for col in str_cols:
        df[col] = df[col].str.decode("utf-8")
    assert df.loc[0, "age"] == 0
    assert df.loc[1, "age"] == 1
    assert df.loc[2, "age"] == 2
    assert df.loc[0, "primary_activity_type"] == "hospital"
    assert df.loc[0, "primary_activity_id"] == dummy_world.hospitals[0].id
    assert df.loc[1, "primary_activity_type"] == "None"
    assert df.loc[1, "primary_activity_id"] == 0
    assert df.loc[1, "residence_type"] == "household"
    assert df.loc[1, "residence_id"] == dummy_world.households[0].id
    assert df.loc[2, "residence_type"] == "care_home"
    assert df.loc[2, "residence_id"] == dummy_world.care_homes[0].id
    assert df.loc[0, "ethnicity"] == "A"
    assert df.loc[1, "ethnicity"] == "B"
    assert df.loc[2, "ethnicity"] == "C"
    assert df.loc[0, "sex"] == "f"
    assert df.loc[2, "sex"] == "m"
    assert len(df['tonto'].values) == len(tonto)
    assert all([pytest.approx(a) == b for a, b in zip(df['tonto'].values, tonto)])
    assert len(df['listo'].values) == len(listo)
    assert all([pytest.approx(a) == b for a, b in zip(df['listo'].values, listo)])
    assert len(df['vaccine_type'].values) == len(vaccine_type)
    assert all([pytest.approx(a) == b for a, b in zip(df['vaccine_type'].values, vaccine_type)])
    assert len(df['vaccine_name'].values) == len(vaccine_name)
    assert all([pytest.approx(a) == b for a, b in zip(df['vaccine_name'].values, vaccine_name)])




def test__static_location(dummy_world):
    record = Record(
        record_path="results",
        record_static_data=True,
    )
    record.static_data(world=dummy_world)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        table = record.file.root.locations
        df = pd.DataFrame.from_records(table.read(), index="id")
    location_types, group_ids = [], []
    for attribute, value in dummy_world.__dict__.items():
        if isinstance(value, Supergroup):
            for group in getattr(dummy_world, attribute):
                location_types.append(group.spec)
                group_ids.append(group.id)

    for index, row in df.iterrows():
        assert row["spec"].decode() == location_types[index]
        assert (
            getattr(dummy_world, location_types[index] + "s")
            .get_from_id(group_ids[index])
            .area.id
            == row["area_id"]
        )
        assert group_ids[index] == row["group_id"]
        if index == 2:
            assert dummy_world.areas.get_from_id(row["area_id"]).name == "area_6"
    assert len(df) == len(dummy_world.households) + len(dummy_world.care_homes) + len(
        dummy_world.hospitals
    )


def test__static_geography(dummy_world):
    record = Record(
        record_path="results",
        record_static_data=True,
    )
    record.static_data(world=dummy_world)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        table = record.file.root.areas
        area_df = pd.DataFrame.from_records(table.read(), index="id")
        assert len(area_df) == len(dummy_world.areas)
        table = record.file.root.super_areas
        super_area_df = pd.DataFrame.from_records(table.read(), index="id")
        assert len(super_area_df) == len(dummy_world.super_areas)
        table = record.file.root.regions
        region_df = pd.DataFrame.from_records(table.read(), index="id")
    assert len(region_df) == len(dummy_world.regions)
    for area in dummy_world.areas:
        assert (
            area.super_area.name
            == super_area_df.loc[area_df.loc[area.id].super_area_id, "name"].decode()
        )
        assert np.isclose(
            area.socioeconomic_index, area_df.loc[area.id]["socioeconomic_index"]
        )

    for super_area in dummy_world.super_areas:
        assert (
            super_area.region.name
            == region_df.loc[
                super_area_df.loc[super_area.id].region_id, "name"
            ].decode()
        )


def test__sumarise_time_tep(dummy_world):
    dummy_world.people = Population(dummy_world.people)

    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    with open_file(record.record_path / record.filename, mode="a") as f:
        record.file = f
        record.accumulate(
            table_name="infections",
            location_spec="care_home",
            region_name="region_1",
            location_id=dummy_world.care_homes[0].id,
            infected_ids=[2],
            infector_ids=[0],
            infection_ids=[0],
        )
        record.accumulate(
            table_name="infections",
            location_spec="household",
            region_name="region_1",
            location_id=dummy_world.households[0].id,
            infected_ids=[0],
            infector_ids=[5],
            infection_ids=[0],
        )
        record.accumulate(
            table_name="hospital_admissions",
            hospital_id=dummy_world.hospitals[0].id,
            patient_id=1,
        )
        record.accumulate(
            table_name="icu_admissions",
            hospital_id=dummy_world.hospitals[0].id,
            patient_id=1,
        )
        record.summarise_time_step(timestamp, dummy_world)
    record.time_step(timestamp)
    timestamp = datetime.datetime(2020, 4, 5)
    record.accumulate(
        table_name="deaths",
        location_spec="care_home",
        location_id=dummy_world.care_homes[0].id,
        dead_person_id=2,
    )
    record.accumulate(
        table_name="deaths",
        location_spec="household",
        location_id=dummy_world.households[0].id,
        dead_person_id=0,
    )
    record.accumulate(
        table_name="deaths",
        location_spec="hospital",
        location_id=dummy_world.hospitals[0].id,
        dead_person_id=1,
    )
    record.summarise_time_step(timestamp, dummy_world)
    record.time_step(timestamp)
    summary_df = pd.read_csv(record.record_path / "summary.csv", index_col=0)
    region_1 = summary_df[summary_df["region"] == "region_1"]
    region_2 = summary_df[summary_df["region"] == "region_2"]
    assert region_1.loc["2020-04-04"]["daily_infected"] == 2
    assert region_1.loc["2020-04-05"]["daily_infected"] == 0
    assert region_2.loc["2020-04-04"]["daily_infected"] == 0
    assert region_2.loc["2020-04-05"]["daily_infected"] == 0

    assert region_1.loc["2020-04-04"]["daily_hospitalised"] == 0
    assert region_2.loc["2020-04-04"]["daily_hospitalised"] == 1
    assert region_2.loc["2020-04-04"]["daily_intensive_care"] == 1
    assert region_1.loc["2020-04-05"]["daily_hospitalised"] == 0
    assert region_1.loc["2020-04-05"]["daily_intensive_care"] == 0
    assert region_2.loc["2020-04-05"]["daily_intensive_care"] == 0

    assert region_1.loc["2020-04-05"]["daily_deaths"] == 3
    assert region_2.loc["2020-04-05"]["daily_deaths"] == 0

    assert region_2.loc["2020-04-05"]["daily_hospital_deaths"] == 1


def test__meta_information():
    record = Record(record_path="results")
    comment = "I love passing tests"
    record.meta_information(comment=comment, random_state=0, number_of_cores=20)
    with open(record.record_path / "config.yaml") as file:
        parameters = yaml.load(file, Loader=yaml.FullLoader)
    assert parameters["meta_information"]["user_comment"] == comment
    assert parameters["meta_information"]["random_state"] == 0
    assert parameters["meta_information"]["number_of_cores"] == 20


def test__parameters(dummy_world, selector, selectors):
    interaction = Interaction.from_file(config_filename=config_interaction)
    interaction.alpha_physical = 100.0
    infection_seed = InfectionSeed.from_uniform_cases(
        world=None,
        infection_selector=selector,
        seed_strength=0.0,
        cases_per_capita=0,
        date="2020-03-01"
    )
    infection_seeds = InfectionSeeds([infection_seed])
    infection_seed.min_date = datetime.datetime(2020, 10, 10)
    infection_seed.max_date = datetime.datetime(2020, 10, 11)

    policies = Policies.from_file()
    activity_manager = ActivityManager(
        world=dummy_world,
        policies=policies,
        timer=None,
        all_activities=None,
        activity_to_super_groups={"residence": ["household"]},
    )
    record = Record(record_path="results")
    epidemiology = Epidemiology(
        infection_seeds=infection_seeds, infection_selectors=selectors
    )
    record.parameters(
        interaction=interaction,
        epidemiology=epidemiology,
        activity_manager=activity_manager,
    )
    with open(record.record_path / "config.yaml", "r") as file:
        parameters = yaml.load(file, Loader=yaml.FullLoader)

        #policies = policies.replace("array", "np.array")
        #policies = eval(policies)
    interaction_attributes = ["betas", "alpha_physical"]
    for attribute in interaction_attributes:
        assert parameters["interaction"][attribute] == getattr(interaction, attribute)
    for key, value in interaction.contact_matrices.items():
        np.testing.assert_equal(
            parameters["interaction"]["contact_matrices"][key], value
        )

    assert "Covid19" in parameters["infection_seeds"]
    seed_parameters = parameters["infection_seeds"]["Covid19"]
    assert seed_parameters["seed_strength"] == infection_seed.seed_strength
    assert seed_parameters["min_date"] == infection_seed.min_date.strftime("%Y-%m-%d")
    assert seed_parameters["max_date"] == infection_seed.max_date.strftime("%Y-%m-%d")
    assert "Covid19" in parameters["infections"]
    inf_parameters = parameters["infections"]["Covid19"]
    assert inf_parameters["transmission_type"] == selector.transmission_type
