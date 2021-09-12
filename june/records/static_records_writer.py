import tables
from tables import open_file
import numpy as np

from june.records.helper_records_writer import _get_description_for_event
from june.groups import Supergroup


class StaticRecord:
    def __init__(
        self, hdf5_file, table_name, int_names, float_names, str_names, expectedrows
    ):
        if not isinstance(hdf5_file, tables.file.File):
            raise TypeError("hdf5_file must be an open HDF5 file (use tables.openFile)")
        self.file = hdf5_file
        self.table_name = table_name
        self.int_names = int_names
        self.float_names = float_names
        self.str_names = str_names
        self.expectedrows = expectedrows
        self.extra_int_data = {}
        self.extra_float_data = {}
        self.extra_str_data = {}

    def _create_table(self, int_names, float_names, str_names, expectedrows):
        with open_file(self.file.filename, mode="a") as file:
            table_description = _get_description_for_event(
                int_names=int_names,
                float_names=float_names,
                str_names=str_names,
                timestamp=False,
            )
            self.table = file.create_table(
                file.root,
                self.table_name,
                table_description,
                expectedrows=expectedrows,
            )

    def _record(self, hdf5_file, int_data, float_data, str_data):
        data = np.rec.fromarrays(
            [np.array(data, dtype=np.uint32) for data in int_data]
            + [np.array(data, dtype=np.float32) for data in float_data]
            + [np.array(data, dtype="S20") for data in str_data]
        )
        table = getattr(hdf5_file.root, self.table_name)
        table.append(data)
        table.flush()

    def get_data(self, world):
        pass

    def record(self, hdf5_file, world):
        int_data, float_data, str_data = self.get_data(world=world)
        if self.extra_int_data is not None:
            self.int_names += list(self.extra_int_data.keys())
            for value in self.extra_int_data.values():
                int_data += [value]
        if self.extra_float_data is not None:
            self.float_names += list(self.extra_float_data.keys())
            for value in self.extra_float_data.values():
                float_data += [value]
        if self.extra_str_data is not None:
            self.str_names += list(self.extra_str_data.keys())
            for value in self.extra_str_data.values():
                str_data += [value]
        self._create_table(self.int_names, self.float_names, self.str_names, self.expectedrows)
        self._record(
            hdf5_file=hdf5_file,
            int_data=int_data,
            float_data=float_data,
            str_data=str_data,
        )


class PeopleRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="population",
            int_names=[
                "id",
                "age",
                "primary_activity_id",
                "residence_id",
                "area_id",
            ],
            float_names=[],
            str_names=["sex", "ethnicity", "primary_activity_type", "residence_type",],
            expectedrows=1_000_000,
        )

        self.extra_float_data = {}
        self.extra_int_data = {}
        self.extra_str_data = {}

    def get_data(self, world):
        (
            ids,
            age,
            primary_activity_type,
            primary_activity_id,
            residence_type,
            residence_id,
            area_id,
            sex,
            ethnicity,
        ) = ([], [], [], [], [], [], [], [], [])
        for person in world.people:
            ids.append(person.id)
            age.append(person.age)
            primary_activity_type.append(
                person.primary_activity.group.spec
                if person.primary_activity is not None
                else f"None"
            )
            primary_activity_id.append(
                person.primary_activity.group.id
                if person.primary_activity is not None
                else 0
            )
            residence_type.append(
                person.residence.group.spec if person.residence is not None else f"None"
            )
            residence_id.append(
                person.residence.group.id if person.residence is not None else 0
            )
            area_id.append(person.area.id if person.area is not None else 0)
            sex.append(person.sex)
            ethnicity.append(person.ethnicity if person.ethnicity is not None else "None")
        int_data = [
            ids,
            age,
            primary_activity_id,
            residence_id,
            area_id,
        ]
        float_data = []
        str_data = []
        str_data = [sex, ethnicity, primary_activity_type, residence_type]
        return int_data, float_data, str_data


class LocationRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="locations",
            int_names=["id", "group_id", "area_id"],
            float_names=["latitude", "longitude"],
            str_names=["spec"],
            expectedrows=1_000_000,
        )

    def get_data(self, world):
        (ids, latitude, longitude, group_spec, group_id, area_id) = (
            [],
            [],
            [],
            [],
            [],
            [],
        )
        counter = 0
        for attribute, value in world.__dict__.items():
            if isinstance(value, Supergroup) and attribute not in (
                "cities",
                "cemeteries",
                "stations",
            ):
                for group in getattr(world, attribute):
                    if group.external:
                        continue
                    ids.append(counter)
                    group_spec.append(group.spec)
                    group_id.append(group.id)
                    area_id.append(group.area.id)
                    latitude.append(group.coordinates[0])
                    longitude.append(group.coordinates[1])
                    counter += 1
        int_data = [ids, group_id, area_id]
        float_data = [latitude, longitude]
        str_data = [group_spec]
        return int_data, float_data, str_data


class AreaRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="areas",
            int_names=["id", "super_area_id",],
            float_names=["latitude", "longitude", "socioeconomic_index"],
            str_names=["name"],
            expectedrows=10_000,
        )

    def get_data(self, world):
        (
            area_id, 
            super_area_id, 
            latitude, 
            longitude, 
            socioeconomic_index, 
            area_name
        ) = ([], [], [], [], [], [])
        if world.areas is not None:
            for area in world.areas:
                area_id.append(area.id)
                super_area_id.append(area.super_area.id)
                latitude.append(area.coordinates[0])
                longitude.append(area.coordinates[1])
                socioeconomic_index.append(area.socioeconomic_index)
                area_name.append(area.name)
        int_data = [area_id, super_area_id]
        float_data = [latitude, longitude, socioeconomic_index]
        str_data = [area_name]
        return int_data, float_data, str_data


class SuperAreaRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="super_areas",
            int_names=["id", "region_id",],
            float_names=["latitude", "longitude"],
            str_names=["name"],
            expectedrows=5_000,
        )

    def get_data(self, world):
        super_area_id, region_id, latitude, longitude, super_area_name = (
            [],
            [],
            [],
            [],
            [],
        )
        if world.super_areas is not None:
            for super_area in world.super_areas:
                super_area_id.append(super_area.id)
                region_id.append(super_area.region.id)
                latitude.append(super_area.coordinates[0])
                longitude.append(super_area.coordinates[1])
                super_area_name.append(super_area.name)
        int_data = [super_area_id, region_id]
        float_data = [latitude, longitude]
        str_data = [super_area_name]
        return int_data, float_data, str_data


class RegionRecord(StaticRecord):
    def __init__(self, hdf5_file):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="regions",
            int_names=["id",],
            float_names=[],
            str_names=["name"],
            expectedrows=50,
        )

    def get_data(self, world):
        region_id, region_name = [], []
        if world.regions is not None:
            for region in world.regions:
                region_id.append(region.id)
                region_name.append(region.name)
        int_data = [region_id]
        float_data = []
        str_data = [region_name]
        return int_data, float_data, str_data
