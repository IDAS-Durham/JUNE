import datetime
import numpy as np
import json
import pandas as pd
import yaml
import pytest
from pathlib import Path

from tables import open_file
from june import paths
from june.records import Record
from june.groups import Hospital, Hospitals, Household, Households, CareHome, CareHomes
from june.policy import Policies
from june.activity import ActivityManager
from june.demography import Person, Population
from june.interaction import Interaction
from june.epidemiology.infection import InfectionSelector, HealthIndexGenerator
from june.epidemiology.infection_seed import InfectionSeed
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

from june.records.records_writer import prepend_checkpoint_hdf5

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


def test__prepend_checkpoint_hdf5(dummy_world):

    pre_checkpoint_record_path = Path("./pre_checkpoint_results/june_record.h5")
    pre_checkpoint_record = Record(
        record_path="pre_checkpoint_results", record_static_data=True
    )
    pre_checkpoint_record.static_data(dummy_world)
    for i in range(1, 15):
        timestamp = datetime.datetime(2020, 3, i)
        ## everyone from the second record should have an EVEN id.
        infected_ids = [i * 1000 + 500 + 0 + 2 * x for x in range(3)]
        infector_ids = [i * 1000 + 500 + 10 + 2 * x for x in range(3)]
        dead_ids = [i * 1000 + 500 + 20 + 2 * x for x in range(3)]
        infection_ids = [i * 1000 + 500 + 20 + 2 * x for x in range(3)]
        with open_file(pre_checkpoint_record_path, mode="a") as f:
            pre_checkpoint_record.file = f
            pre_checkpoint_record.accumulate(
                table_name="infections",
                location_spec="pre_check_location",
                region_name="over_here",
                location_id=0,
                infected_ids=infected_ids,
                infector_ids=infector_ids,
                infection_ids=infection_ids,
            )
            for dead_id in dead_ids:
                pre_checkpoint_record.accumulate(
                    table_name="deaths",
                    location_id=0,
                    location_spec="pre_check_location",
                    dead_person_id=dead_id,
                )
        pre_checkpoint_record.time_step(timestamp)

    post_checkpoint_record_path = Path("./post_checkpoint_results/june_record.h5")
    post_checkpoint_record = Record(
        record_path="post_checkpoint_results", record_static_data=True
    )
    post_checkpoint_record.static_data(dummy_world)
    for i in range(11, 21):
        timestamp = datetime.datetime(2020, 3, i)
        ## everyone from the second record should have an ODD id.
        infected_ids = [i * 1000 + 500 + 0 + 2 * x + 1 for x in range(3)]
        infector_ids = [i * 1000 + 500 + 10 + 2 * x + 1 for x in range(3)]
        dead_ids = [i * 1000 + 500 + 20 + 2 * x + 1 for x in range(3)]
        infection_ids = [i * 1000 + 500 + 20 + 2 * x + 1 for x in range(3)]
        with open_file(post_checkpoint_record_path, mode="a") as f:
            post_checkpoint_record.file = f
            post_checkpoint_record.accumulate(
                table_name="infections",
                location_spec="post_check_location",
                region_name="way_over_there",
                location_id=0,
                infected_ids=infected_ids,
                infector_ids=infector_ids,
                infection_ids=infection_ids,
            )
            for dead_id in dead_ids:
                post_checkpoint_record.accumulate(
                    table_name="deaths",
                    location_id=0,
                    location_spec="pre_check_location",
                    dead_person_id=dead_id,
                )
        post_checkpoint_record.time_step(timestamp)

    merged_record_path = Path("./post_checkpoint_results/merged_checkpoint_record.h5")
    prepend_checkpoint_hdf5(
        pre_checkpoint_record_path,
        post_checkpoint_record_path,
        merged_record_path=merged_record_path,
        checkpoint_date=datetime.datetime(2020, 3, 11),
    )

    with open_file(merged_record_path) as merged_record:
        unique_infection_dates = np.unique(
            [
                datetime.datetime.strptime(x.decode("utf-8"), "%Y-%m-%d")
                for x in merged_record.root.infections[:]["timestamp"]
            ]
        )

        assert len(unique_infection_dates) == 20
        assert len(merged_record.root.infections[:]) == 3 * 20

        for row in merged_record.root.infections[:]:
            timestamp = datetime.datetime.strptime(
                row["timestamp"].decode("utf-8"), "%Y-%m-%d"
            )
            if timestamp < datetime.datetime(2020, 3, 11):
                assert row["infected_ids"] % 2 == 0
                assert row["infector_ids"] % 2 == 0
            else:
                assert row["infected_ids"] % 2 == 1
                assert row["infector_ids"] % 2 == 1

        for row in merged_record.root.deaths[:]:
            timestamp = datetime.datetime.strptime(
                row["timestamp"].decode("utf-8"), "%Y-%m-%d"
            )
            if timestamp < datetime.datetime(2020, 3, 11):
                assert row["dead_person_ids"] % 2 == 0
            else:
                assert row["dead_person_ids"] % 2 == 1
