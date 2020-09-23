import tables
import numpy as np

from june.records.helper_records_writer import _get_description_for_event
from june.groups import Supergroup


class StaticRecord:
    def __init__(self, hdf5_file, table_name, int_names, float_names, str_names, expectedrows):
        if not isinstance(hdf5_file, tables.file.File):
            raise TypeError("hdf5_file must be an open HDF5 file (use tables.openFile)")
        self.file = hdf5_file
        self.table_name = table_name
        self._create_table(int_names, float_names, str_names, expectedrows)

    def _create_table(self, int_names, float_names, str_names, expectedrows):
        table_description = _get_description_for_event(
            int_names=int_names,
            float_names=float_names,
            str_names=str_names,
            timestamp=False,
        )
        self.table = self.file.create_table(
            self.file.root,
            self.table_name,
            table_description,
            expectedrows=expectedrows,
        )

    def _record(self, hdf5_file, int_data, float_data, str_data):
        data = np.rec.fromarrays(
            [np.array(data, dtype=np.int32) for data in int_data]
            + [np.array(data, dtype=np.float32) for data in float_data]
            + [np.array(data, dtype="S20") for data in str_data]
        )
        table = getattr(hdf5_file.root, self.table_name)
        table.append(data)
        table.flush()

    def get_data(self, world, get_global_location_id):
        pass

    def record(self, hdf5_file, world, get_global_location_id):
        int_data, float_data, str_data = self.get_data(world=world, get_global_location_id=get_global_location_id)
        self._record(
            hdf5_file=hdf5_file,
            int_data=int_data,
            float_data = float_data,
            str_data=str_data
        )



class PeopleRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="population",
            int_names=[
                "id",
                "age",
                "socioeconomic_index",
                "primary_activity_id",
                "residence_id",
            ],
            float_names=[],
            str_names=["sex", "ethnicity"],
            expectedrows=1_000_000,
        )

    def get_data(self, world, get_global_location_id):
        (
            ids,
            age,
            socioeconomic_index,
            primary_activity_id,
            residence_id,
            sex,
            ethnicity,
        ) = ([], [], [], [], [], [], [])
        for person in world.people:
            ids.append(person.id)
            age.append(person.age)
            socioeconomic_index.append(person.socioecon_index)
            primary_activity = (
                f"{person.primary_activity.group.spec}_{person.primary_activity.group.id}"
                if person.primary_activity is not None
                else f"None"
            )
            primary_activity_id.append(get_global_location_id(primary_activity))
            residence = (
                f"{person.residence.group.spec}_{person.residence.group.id}"
                if person.residence is not None
                else f"None"
            )
            residence_id.append(get_global_location_id(residence))
            sex.append(person.sex)
            ethnicity.append(person.ethnicity)
        int_data=[ids, age, socioeconomic_index, primary_activity_id, residence_id]
        float_data = []
        str_data = [sex, ethnicity]
        return int_data, float_data, str_data

class LocationRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="locations",
            int_names=[
                "id",
                "area_id",
            ],
            float_names=["latitude", "longitude"],
            str_names=["type"],
            expectedrows=1_000_000,
        )

    def get_data(self, world, get_global_location_id):
        (
            ids,
            latitude,
            longitude,
            location_type,
            area_id
        ) = ([], [], [], [],[])
        for attribute, value in world.__dict__.items():
            if isinstance(value, Supergroup):
                for group in getattr(world, attribute):
                    ids.append(get_global_location_id(f"{group.spec}_{group.id}"))
                    latitude.append(group.coordinates[0])
                    longitude.append(group.coordinates[1])
                    location_type.append(group.spec)
                    area_id.append(group.area.id)
        int_data=[ids, area_id]
        float_data = [latitude, longitude]
        str_data = [location_type]
        return int_data, float_data, str_data

class AreaRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="areas",
            int_names=[
                "id",
                "super_area_id",
            ],
            float_names=["latitude", "longitude"],
            str_names=["name"],
            expectedrows=10_000,
        )

    def get_data(self, world, get_global_location_id):
        area_id, super_area_id, latitude, longitude, area_name = [], [], [], [], []
        for area in world.areas:
            area_id.append(area.id)
            super_area_id.append(area.super_area.id)
            latitude.append(area.coordinates[0])
            longitude.append(area.coordinates[1])
            area_name.append(area.name)
        int_data=[area_id, super_area_id]
        float_data = [latitude, longitude]
        str_data = [area_name]
        return int_data, float_data, str_data

class SuperAreaRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="super_areas",
            int_names=[
                "id",
                "region_id",
            ],
            float_names=["latitude", "longitude"],
            str_names=["name"],
            expectedrows=5_000,
        )

    def get_data(self, world, get_global_location_id):
        super_area_id, region_id, latitude, longitude, super_area_name = [], [], [], [], []
        for super_area in world.super_areas:
            super_area_id.append(super_area.id)
            region_id.append(super_area.region.id)
            latitude.append(super_area.coordinates[0])
            longitude.append(super_area.coordinates[1])
            super_area_name.append(super_area.name)
        int_data=[super_area_id, region_id]
        float_data = [latitude, longitude]
        str_data = [super_area_name]
        return int_data, float_data, str_data

class RegionRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="regions",
            int_names=[
                "id",
            ],
            float_names=[],
            str_names=["name"],
            expectedrows=50,
        )

    def get_data(self, world, get_global_location_id):
        region_id, region_name = [], []
        for region in world.regions:
            region_id.append(region.id)
            region_name.append(region.name)
        int_data=[region_id]
        float_data = []
        str_data = [region_name]
        return int_data, float_data, str_data


