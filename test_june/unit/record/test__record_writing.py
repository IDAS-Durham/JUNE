import datetime
import numpy as np
import pandas as pd
from june.records import Record

def test__locations_id():
    locations_to_store = {'household':5, 'care_home': 4, 'school': 3, 'grocery':1}
    record = Record(record_path="results", filename="test3.hdf5", 
            locations_to_store=locations_to_store)

    global_id = record.get_global_location_id('household_2')
    assert global_id == 2
    global_id = record.get_global_location_id('care_home_2')
    assert global_id == 7
    global_id = record.get_global_location_id('school_0')
    assert global_id == 9
    record.file.close()

def test__writing_infections():
    record = Record(record_path="results", filename="test.hdf5")
    time_stamp = datetime.datetime(2020, 10, 10)
    record.infections(
        time_stamp=time_stamp, location='care_home_0', new_infected_ids=[0, 10, 20]
    )
    df = pd.DataFrame.from_records(record.infection_table.read())
    assert len(df) == 3
    assert (
        df.time_stamp.unique()[0].decode()
        == "2020-10-10"
    )
    assert df.location_id.unique() == [1]
    assert len(df.infected_id) == 3
    assert df.infected_id[0] == 0
    assert df.infected_id[1] == 10
    assert df.infected_id[2] == 20
    del df
    record.file.close()

def test__writing_hospital_admissions():
    record = Record(record_path="results", filename="test2.hdf5")
    time_stamp = datetime.datetime(2020, 4, 4)
    record.hospital_admission(time_stamp=time_stamp, hospital_id=0, patient_id=10)
    df = pd.DataFrame.from_records(record.hosp_admission_table.read())
    assert len(df) == 1
    assert (
            df.time_stamp.iloc[0].decode()
        == "2020-04-04"
    )
    assert df.hospital_id.iloc[0] == 0
    assert df.patient_id.iloc[0] == 10
    record.file.close()


