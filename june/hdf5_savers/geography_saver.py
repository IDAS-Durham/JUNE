import h5py
import numpy as np

from june.geography import Geography, Area, SuperArea, Areas, SuperAreas
from june.world import World

nan_integer = -999


def save_geography_to_hdf5(geography: Geography, file_path: str):
    """
    Saves the households object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_beds, n_icu_beds, super_area, coordinates

    Parameters
    ----------
    companies 
        population object
    file_path
        path of the saved hdf5 file
    chunk_size
        number of people to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_areas = len(geography.areas)
    area_ids = []
    area_names = []
    area_super_areas = []
    area_coordinates = []
    n_super_areas = len(geography.super_areas)
    super_area_ids = []
    super_area_names = []
    super_area_coordinates = []
    super_area_city = []
    super_area_closest_commuting_city = []
    super_area_closest_station = []

    for area in geography.areas:
        area_ids.append(area.id)
        area_super_areas.append(area.super_area.id)
        area_names.append(area.name.encode("ascii", "ignore"))
        area_coordinates.append(np.array(area.coordinates, dtype=np.float))

    for super_area in geography.super_areas:
        super_area_ids.append(super_area.id)
        super_area_names.append(super_area.name.encode("ascii", "ignore"))
        super_area_coordinates.append(np.array(super_area.coordinates))
        if super_area.city is None:
            super_area_city.append(nan_integer)
        else:
            super_area_city.append(super_area.city.id)
        if super_area.closest_commuting_city is None:
            super_area_closest_commuting_city.append(nan_integer)
        else:
            super_area_closest_commuting_city.append(
                super_area.closest_commuting_city.id
            )
        if super_area.closest_station is None:
            super_area_closest_station.append(nan_integer)
        else:
            super_area_closest_station.append(super_area.closest_station.id)

    area_ids = np.array(area_ids, dtype=np.int)
    area_names = np.array(area_names, dtype="S20")
    area_super_areas = np.array(area_super_areas, dtype=np.int)
    area_coordinates = np.array(area_coordinates, dtype=np.float)
    super_area_ids = np.array(super_area_ids, dtype=np.int)
    super_area_names = np.array(super_area_names, dtype="S20")
    super_area_coordinates = np.array(super_area_coordinates, dtype=np.float)
    super_area_city = np.array(super_area_city, dtype=np.int)
    super_area_closest_commuting_city = np.array(
        super_area_closest_commuting_city, dtype=np.int
    )
    super_area_closest_station = np.array(super_area_closest_station, dtype=np.int)

    with h5py.File(file_path, "a") as f:
        geography_dset = f.create_group("geography")
        geography_dset.attrs["n_areas"] = n_areas
        geography_dset.attrs["n_super_areas"] = n_super_areas
        geography_dset.create_dataset("area_id", data=area_ids)
        geography_dset.create_dataset("area_name", data=area_names)
        geography_dset.create_dataset("area_super_area", data=area_super_areas)
        geography_dset.create_dataset("area_coordinates", data=area_coordinates)
        geography_dset.create_dataset("super_area_id", data=super_area_ids)
        geography_dset.create_dataset("super_area_name", data=super_area_names)
        geography_dset.create_dataset("super_area_city", data=super_area_city)
        geography_dset.create_dataset(
            "super_area_closest_commuting_city", data=super_area_closest_commuting_city
        )
        geography_dset.create_dataset(
            "super_area_closest_station", data=super_area_closest_station
        )
        geography_dset.create_dataset(
            "super_area_coordinates", data=super_area_coordinates
        )


def load_geography_from_hdf5(file_path: str, chunk_size=50000):
    """
    Loads geography from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        geography = f["geography"]
        n_areas = geography.attrs["n_areas"]
        area_list = []
        n_super_areas = geography.attrs["n_super_areas"]
        # areas
        n_chunks = int(np.ceil(n_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_areas)
            length = idx2 - idx1
            area_ids = np.empty(length, dtype=int)
            geography["area_id"].read_direct(
                area_ids, np.s_[idx1:idx2], np.s_[0:length]
            )
            area_names = np.empty(length, dtype="S20")
            geography["area_name"].read_direct(
                area_names, np.s_[idx1:idx2], np.s_[0:length]
            )
            area_coordinates = np.empty((length, 2), dtype=float)
            geography["area_coordinates"].read_direct(
                area_coordinates, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(length):
                area = Area(
                    name=area_names[k].decode(),
                    super_area=None,
                    coordinates=area_coordinates[k],
                )
                area.id = area_ids[k]
                area_list.append(area)
        # super areas
        super_area_list = []
        n_chunks = int(np.ceil(n_super_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_super_areas)
            length = idx2 - idx1
            super_area_ids = np.empty(length, dtype=int)
            geography["super_area_id"].read_direct(
                super_area_ids, np.s_[idx1:idx2], np.s_[0:length]
            )
            super_area_names = np.empty(length, dtype="S20")
            geography["super_area_name"].read_direct(
                super_area_names, np.s_[idx1:idx2], np.s_[0:length]
            )
            super_area_coordinates = np.empty((length, 2), dtype=float)
            geography["super_area_coordinates"].read_direct(
                super_area_coordinates, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(idx2 - idx1):
                super_area = SuperArea(
                    name=super_area_names[k].decode(),
                    areas=None,
                    coordinates=super_area_coordinates[k],
                )
                super_area.id = super_area_ids[k]
                super_area_list.append(super_area)
    areas = Areas(area_list)
    super_areas = SuperAreas(super_area_list)
    return Geography(areas, super_areas)


def restore_geography_properties_from_hdf5(world: World, file_path: str, chunk_size):
    first_super_area_id = world.super_areas[0].id
    first_area_id = world.areas[0].id
    if world.cities:
        first_city_id = world.cities[0].id
    if world.stations:
        first_station_id = world.stations[0].id
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        geography = f["geography"]
        n_areas = geography.attrs["n_areas"]
        n_chunks = int(np.ceil(n_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_areas)
            length = idx2 - idx1
            areas_ids = np.empty(length, dtype=int)
            geography["area_id"].read_direct(
                areas_ids, np.s_[idx1:idx2], np.s_[0:length]
            )
            super_areas = np.empty(length, dtype=int)
            geography["area_super_area"].read_direct(
                super_areas, np.s_[idx1:idx2], np.s_[0:length]
            )
            for k in range(length):
                area = world.areas[areas_ids[k] - first_area_id]
                area.super_area = world.super_areas[
                    super_areas[k] - first_super_area_id
                ]
                area.super_area.areas.append(area)
        n_super_areas = geography.attrs["n_super_areas"]
        super_area_ids = geography["super_area_id"]
        super_area_cities = geography["super_area_city"]
        super_area_closest_commuting_city = geography[
            "super_area_closest_commuting_city"
        ]
        super_area_closest_station = geography["super_area_closest_station"]
        for k in range(n_super_areas):
            super_area = world.super_areas[super_area_ids[k] - first_super_area_id]
            if world.cities:
                if super_area_cities[k] != nan_integer:
                    super_area.city = world.cities[super_area_cities[k] - first_city_id]
                if super_area_closest_commuting_city[k] != nan_integer:
                    super_area.closest_commuting_city = world.cities[
                        super_area_closest_commuting_city[k] - first_city_id
                    ]
            if world.stations:
                if super_area_closest_station[k] != nan_integer:
                    super_area.closest_station = world.stations[
                        super_area_closest_station[k] - first_station_id
                    ]
