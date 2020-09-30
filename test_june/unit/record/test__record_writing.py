import datetime
import numpy as np
import pandas as pd
import pytest
from tables import open_file
from june import paths
from june.records import Record
from june.groups import Hospital, Hospitals, Household, Households, CareHome, CareHomes
from june.demography import Person, Population
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
        Area(name="area_1", coordinates=(0.0, 0.0), super_area=super_areas[0]),
        Area(name="area_2", coordinates=(0.0, 0.0), super_area=super_areas[0]),
        Area(name="area_3", coordinates=(0.0, 0.0), super_area=super_areas[0]),
    ]
    super_areas[1].areas = [
        Area(name="area_4", coordinates=(0.0, 0.0), super_area=super_areas[1]),
        Area(name="area_5", coordinates=(0.0, 0.0), super_area=super_areas[1]),
    ]
    super_areas[2].areas = [
        Area(name="area_6", coordinates=(5, 5), super_area=super_areas[2])
    ]
    areas = Areas(super_areas[0].areas + super_areas[1].areas + super_areas[2].areas)
    households = Households([Household(area=super_areas[0].areas[0])])
    hospitals = Hospitals(
        [Hospital(n_beds=1, n_icu_beds=1, area=areas[5], coordinates=(0.0, 0.0),)]
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
        Person.from_attributes(id=0, age=0, ethnicity="A", socioecon_index=0),
        Person.from_attributes(id=1, age=1, ethnicity="B", socioecon_index=1),
        Person.from_attributes(id=2, age=2, sex="m", ethnicity="C", socioecon_index=2),
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
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate(
        table_name="infections", location_spec="care_home", location_id=0, infected_id=0
    )
    record.accumulate(
        table_name="infections",
        location_spec="care_home",
        location_id=0,
        infected_id=10,
    )
    record.accumulate(
        table_name="infections",
        location_spec="care_home",
        location_id=0,
        infected_id=20,
    )
    record.events["infections"].record(hdf5_file=record.file, timestamp=timestamp)
    table = record.file.root.infections
    df = pd.DataFrame.from_records(table.read())
    record.file.close()
    assert len(df) == 3
    assert df.timestamp.unique()[0].decode() == "2020-10-10"
    assert df.location_ids.unique() == [0]
    assert df.location_specs.unique() == [b"care_home"]
    assert len(df.infected_ids) == 3
    assert df.infected_ids[0] == 0
    assert df.infected_ids[1] == 10
    assert df.infected_ids[2] == 20
    del df


def test__writing_hospital_admissions():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate(table_name="hospital_admissions", hospital_id=0, patient_id=10)
    record.events["hospital_admissions"].record(
        hdf5_file=record.file, timestamp=timestamp
    )
    table = record.file.root.hospital_admissions
    df = pd.DataFrame.from_records(table.read())
    record.file.close()
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10


def test__writing_hospital_discharges():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate(table_name='discharges', hospital_id=0, patient_id=10)
    record.events["discharges"].record(
        hdf5_file=record.file, timestamp=timestamp
    )
    table = record.file.root.discharges
    df = pd.DataFrame.from_records(table.read())
    record.file.close()
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10


def test__writing_intensive_care_admissions():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate(table_name="icu_admissions", hospital_id=0, patient_id=10)
    record.events["icu_admissions"].record(hdf5_file=record.file, timestamp=timestamp)
    table = record.file.root.icu_admissions
    df = pd.DataFrame.from_records(table.read())
    record.file.close()
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10


def test__writing_death():
    record = Record(record_path="results")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate(
        table_name="deaths", location_spec="household", location_id=0, dead_person_id=10
    )
    record.events["deaths"].record(hdf5_file=record.file, timestamp=timestamp)
    table = record.file.root.deaths
    df = pd.DataFrame.from_records(table.read())
    record.file.close()
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.location_specs.iloc[0].decode() == "household"
    assert df.location_ids.iloc[0] == 0
    assert df.dead_person_ids.iloc[0] == 10


def test__static_people(dummy_world):
    record = Record(
        record_path="results", record_static_data=True,
    )
    record.static_data(world=dummy_world)
    record.file = open_file(record.record_path / record.filename, mode="a")
    table = record.file.root.population
    df = pd.DataFrame.from_records(table.read(), index="id")
    record.file.close()
    str_cols = record.statics["people"].str_names
    for col in str_cols:
        df[col] = df[col].str.decode("utf-8")
    assert df.loc[0, "age"] == 0
    assert df.loc[1, "age"] == 1
    assert df.loc[2, "age"] == 2
    assert df.loc[0, "socioeconomic_index"] == 0
    assert df.loc[1, "socioeconomic_index"] == 1
    assert df.loc[2, "socioeconomic_index"] == 2
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


def test__static_location(dummy_world):
    record = Record(
        record_path="results", record_static_data=True,
    )
    record.static_data(world=dummy_world)
    record.file = open_file(record.record_path / record.filename, mode="a")
    table = record.file.root.locations
    df = pd.DataFrame.from_records(table.read(), index="id")
    record.file.close()
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
        record_path="results", record_static_data=True,
    )
    record.static_data(world=dummy_world)
    record.file = open_file(record.record_path / record.filename, mode="a")
    table = record.file.root.areas
    area_df = pd.DataFrame.from_records(table.read(), index="id")
    assert len(area_df) == len(dummy_world.areas)
    table = record.file.root.super_areas
    super_area_df = pd.DataFrame.from_records(table.read(), index="id")
    assert len(super_area_df) == len(dummy_world.super_areas)
    table = record.file.root.regions
    region_df = pd.DataFrame.from_records(table.read(), index="id")
    record.file.close()
    assert len(region_df) == len(dummy_world.regions)
    for area in dummy_world.areas:
        assert (
            area.super_area.name
            == super_area_df.loc[area_df.loc[area.id].super_area_id, "name"].decode()
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
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate(
        table_name="infections",
        location_spec="care_home",
        location_id=dummy_world.care_homes[0].id,
        infected_id=2,
    )
    record.accumulate(
        table_name="infections",
        location_spec="household",
        location_id=dummy_world.households[0].id,
        infected_id=0,
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
    record.file.close()
    summary_df = pd.read_csv(record.record_path / "summary.0.csv", index_col=0)
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
