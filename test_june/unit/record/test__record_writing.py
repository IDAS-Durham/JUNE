import datetime
import numpy as np
import pandas as pd
import pytest
from tables import open_file 
from june import paths
from june.records import Record
from june.groups import Hospital, Hospitals

@pytest.fixture(name="hospitals", scope="module")
def create_hospitals():
    return Hospitals(
            [Hospital(n_beds=5, n_icu_beds=1, super_area='E02004935', coordinates=(0.,10.)),
            Hospital(n_beds=5, n_icu_beds=1, super_area='E02005815', coordinates=(10.,0.)),
            ]
            )

    return Hospitals.from_file(filename=paths.data_path / 'input/hospitals/trusts.csv')

def test__locations_id():
    locations_to_store = {"household": 5, "care_home": 4, "school": 3, "grocery": 1}
    record = Record(
        record_path="results",
        filename="test.hdf5",
        locations_to_store=locations_to_store,
    )

    global_id = record.get_global_location_id("household_2")
    assert global_id == 2
    global_id = record.get_global_location_id("care_home_2")
    assert global_id == 7
    global_id = record.get_global_location_id("school_0")
    assert global_id == 9

    location_type, location_id = record.invert_global_location_id(2)
    assert location_type == 'household'
    assert location_id == 2

    location_type, location_id = record.invert_global_location_id(7)
    assert location_type == 'care_home'
    assert location_id == 2

    location_type, location_id = record.invert_global_location_id(9)
    assert location_type == 'school'
    assert location_id == 0



def test__writing_infections():
    record = Record(record_path="results", filename="test.hdf5")
    time_stamp = datetime.datetime(2020, 10, 10)
    record.file = open_file(record.record_path / record.filename, mode='a')
    record.accumulate_infections(
        location="care_home_0", new_infected_ids=[0, 10, 20]
    )
    record.infections(time_stamp=time_stamp)
    table = record.file.root.infections
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 3
    assert df.time_stamp.unique()[0].decode() == "2020-10-10"
    assert df.location_id.unique() == [1]
    assert len(df.infected_id) == 3
    assert df.infected_id[0] == 0
    assert df.infected_id[1] == 10
    assert df.infected_id[2] == 20
    del df
    record.file.close()


def test__writing_hospital_admissions():
    record = Record(record_path="results", filename="test.hdf5")
    time_stamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode='a')
    record.accumulate_hospitalisation(hospital_id=0, patient_id=10)
    record.hospital_admissions(time_stamp=time_stamp)
    table = record.file.root.hospital_admissions
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert (
            df.time_stamp.iloc[0].decode()
        == "2020-04-04"
    )
    assert df.hospital_id.iloc[0] == 0
    assert df.patient_id.iloc[0] == 10
    record.file.close()

def test__writing_intensive_care_admissions():
    record = Record(record_path="results", filename="test.hdf5")
    time_stamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode='a')
    record.accumulate_hospitalisation(hospital_id=0, patient_id=10, intensive_care=True)
    record.intensive_care_admissions(time_stamp=time_stamp)
    table = record.file.root.icu_admissions
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert (
            df.time_stamp.iloc[0].decode()
        == "2020-04-04"
    )
    assert df.hospital_id.iloc[0] == 0
    assert df.patient_id.iloc[0] == 10
    record.file.close()



def test__writing_death():
    record = Record(record_path="results", filename="test.hdf5")
    time_stamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode='a')
    record.accumulate_death(death_location='household_3', dead_person_id=10)
    record.deaths(time_stamp=time_stamp)
    table = record.file.root.deaths
    df = pd.DataFrame.from_records(table.read())
    assert len(df) == 1
    assert (
            df.time_stamp.iloc[0].decode()
        == "2020-04-04"
    )
    assert df.death_location_id.iloc[0] == 3 
    assert df.dead_person_id.iloc[0] == 10
    record.file.close()

def test__sumarise_time_tep(hospitals):
    record = Record(record_path="results", filename="test.hdf5")
    time_stamp = datetime.datetime(2020, 4, 4)
    record.file = open_file(record.record_path / record.filename, mode='a')
    record.accumulate_hospitalisation(hospital_id=0, patient_id=10)
    record.accumulate_hospitalisation(hospital_id=1, patient_id=1)
    record.summarise_time_step('2020-04-04', hospitals)
    assert 1 ==0

