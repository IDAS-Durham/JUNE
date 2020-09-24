import datetime
import numpy as np
import pandas as pd
import pytest
from tables import open_file
from june import paths
from june.records import Record
from june.groups import Hospital, Hospitals, Household, Households, CareHome, CareHomes
from june.demography import Person
from june.demography.geography import (
    Areas,
    SuperAreas,
    Regions,
    Area,
    SuperArea,
    Region,
)
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
    households[0].id = 0
    hospitals = Hospitals(
        [Hospital(n_beds=1, n_icu_beds=1, area=areas[5], coordinates=(0.0, 0.0),)]
    )
    hospitals[0].id = 0
    care_homes = CareHomes([CareHome(area=super_areas[0].areas[1])])
    care_homes[0].id = 0
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


def test__locations_id():
    locations_counts = {"household": 5, "care_home": 4, "school": 3, "grocery": 1}
    record = Record(
        record_path="results", filename="test.hdf5", locations_counts=locations_counts,
    )

    global_id = record.get_global_location_id("infection_seed_0")
    assert global_id == -1
    global_id = record.get_global_location_id("household_2")
    assert global_id == 2
    global_id = record.get_global_location_id("care_home_2")
    assert global_id == 7
    global_id = record.get_global_location_id("school_0")
    assert global_id == 9

    location_type, location_id = record.invert_global_location_id(-1)
    assert location_type == "infection_seed"
    assert location_id == 0

    location_type, location_id = record.invert_global_location_id(2)
    assert location_type == "household"
    assert location_id == 2

    location_type, location_id = record.invert_global_location_id(7)
    assert location_type == "care_home"
    assert location_id == 2

    location_type, location_id = record.invert_global_location_id(9)
    assert location_type == "school"
    assert location_id == 0


def test__writing_infections():
    record = Record(record_path="results", filename="test.hdf5")
    timestamp = datetime.datetime(2020, 10, 10)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate_infections(location="care_home_0", new_infected_ids=[0, 10, 20])
    record.events["infections"].record(hdf5_file=record.file, timestamp=timestamp)
    table = record.file.root.infections
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 3
    assert df.timestamp.unique()[0].decode() == "2020-10-10"
    assert df.infection_location_ids.unique() == [1]
    assert len(df.new_infected_ids) == 3
    assert df.new_infected_ids[0] == 0
    assert df.new_infected_ids[1] == 10
    assert df.new_infected_ids[2] == 20
    del df
    record.file.close()


def test__writing_hospital_admissions():
    record = Record(record_path="results", filename="test.hdf5")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate_hospitalisation(hospital_id=0, patient_id=10)
    record.events["hospital_admissions"].record(
        hdf5_file=record.file, timestamp=timestamp
    )
    table = record.file.root.hospital_admissions
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10
    record.file.close()


def test__writing_intensive_care_admissions():
    record = Record(record_path="results", filename="test.hdf5")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate_hospitalisation(hospital_id=0, patient_id=10, intensive_care=True)
    record.events["icu_admissions"].record(hdf5_file=record.file, timestamp=timestamp)
    table = record.file.root.icu_admissions
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.hospital_ids.iloc[0] == 0
    assert df.patient_ids.iloc[0] == 10
    record.file.close()


def test__writing_death():
    record = Record(record_path="results", filename="test.hdf5")
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate_death(death_location="household_3", dead_person_id=10)
    record.events["deaths"].record(hdf5_file=record.file, timestamp=timestamp)
    table = record.file.root.deaths
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert df.timestamp.iloc[0].decode() == "2020-04-04"
    assert df.death_location_ids.iloc[0] == 3
    assert df.dead_person_ids.iloc[0] == 10
    record.file.close()


def test__static_people(dummy_world):
    record = Record.from_world(
        record_path="results",
        filename="test.hdf5",
        world=dummy_world,
        record_static_data=True,
    )
    record.static_data(world=dummy_world)
    record.file = open_file(record.record_path / record.filename, mode="a")
    table = record.file.root.population
    df = pd.DataFrame.from_records(table.read(), index="id")
    assert df.loc[0, "age"] == 0
    assert df.loc[1, "age"] == 1
    assert df.loc[2, "age"] == 2
    assert df.loc[0, "socioeconomic_index"] == 0
    assert df.loc[1, "socioeconomic_index"] == 1
    assert df.loc[2, "socioeconomic_index"] == 2
    assert record.invert_global_location_id(df.loc[0, "primary_activity_id"]) == (
        "hospital",
        0,
    )
    assert record.invert_global_location_id(df.loc[1, "primary_activity_id"]) == (
        "None",
        0,
    )
    assert record.invert_global_location_id(df.loc[0, "residence_id"]) == (
        "household",
        0,
    )
    assert record.invert_global_location_id(df.loc[2, "residence_id"]) == (
        "care_home",
        0,
    )
    assert df.loc[0, "ethnicity"] == b"A"
    assert df.loc[1, "ethnicity"] == b"B"
    assert df.loc[2, "ethnicity"] == b"C"
    assert df.loc[0, "sex"] == b"f"
    assert df.loc[2, "sex"] == b"m"
    record.file.close()


def test__static_location(dummy_world):
    record = Record.from_world(
        record_path="results",
        filename="test.hdf5",
        world=dummy_world,
        record_static_data=True,
    )
    record.static_data(world=dummy_world)
    record.file = open_file(record.record_path / record.filename, mode="a")
    table = record.file.root.locations
    df = pd.DataFrame.from_records(table.read(), index="id")
    for index, row in df.iterrows():
        location_type, location_id = record.invert_global_location_id(index)
        assert row["type"].decode() == location_type
        assert (
            getattr(dummy_world, location_type + "s")[location_id].area.id
            == row["area_id"]
        )
        if index == 2:
            assert dummy_world.areas[row["area_id"]].name == "area_6"
    assert len(df) == len(dummy_world.households) + len(dummy_world.care_homes) + len(
        dummy_world.hospitals
    )

    record.file.close()


def test__static_geography(dummy_world):
    record = Record.from_world(
        record_path="results",
        filename="test.hdf5",
        world=dummy_world,
        record_static_data=True,
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
    record.file.close()


def test__sumarise_time_tep(dummy_world):
    record = Record(
        record_path="results",
        filename="test.hdf5",
        locations_counts={"household": 1, "care_home": 1, "hospital": 1},
    )
    timestamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode="a")
    record.accumulate_infections(location="care_home_0", new_infected_ids=[2])
    record.accumulate_infections(location="household_0", new_infected_ids=[0])
    record.accumulate_hospitalisation(hospital_id=0, patient_id=1)
    record.accumulate_hospitalisation(hospital_id=0, patient_id=1, intensive_care=True)
    record.summarise_time_step(timestamp, dummy_world)
    record.time_step(timestamp)
    timestamp = datetime.datetime(2020, 4, 5)
    record.accumulate_death(death_location="care_home_0", dead_person_id=2)
    record.accumulate_death(death_location="household_0", dead_person_id=0)
    record.accumulate_death(death_location="hospital_0", dead_person_id=1)
    record.summarise_time_step(timestamp, dummy_world)
    record.time_step(timestamp)
    record.file.close()
    summary_df = pd.read_csv(record.record_path / "summary.csv", index_col=0)
    region_1 = summary_df[summary_df["region"] == "region_1"]
    region_2 = summary_df[summary_df["region"] == "region_2"]
    assert region_1.loc["2020-04-04"]["daily_infections_by_residence"] == 2
    assert region_1.loc["2020-04-05"]["daily_infections_by_residence"] == 0
    assert region_2.loc["2020-04-04"]["daily_infections_by_residence"] == 0
    assert region_2.loc["2020-04-05"]["daily_infections_by_residence"] == 0

    assert region_1.loc["2020-04-04"]["daily_hospital_admissions"] == 0
    assert region_2.loc["2020-04-04"]["daily_hospital_admissions"] == 1
    assert region_2.loc["2020-04-04"]["daily_icu_admissions"] == 1
    assert region_1.loc["2020-04-05"]["daily_hospital_admissions"] == 0
    assert region_1.loc["2020-04-05"]["daily_icu_admissions"] == 0
    assert region_2.loc["2020-04-05"]["daily_icu_admissions"] == 0

    assert region_1.loc["2020-04-05"]["daily_deaths_by_residence"] == 3
    assert region_2.loc["2020-04-05"]["daily_deaths_by_residence"] == 0

    assert region_1.loc["2020-04-05"]["daily_care_home_deaths"] == 1
    assert region_2.loc["2020-04-05"]["daily_hospital_deaths"] == 1
