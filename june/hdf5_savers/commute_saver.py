import h5py
import numpy as np

from june.world import World
from june.geography import City, Cities, Station, Stations
from june.groups.travel import (
    CityTransport,
    CityTransports,
    InterCityTransport,
    InterCityTransports,
)

nan_integer = -999


def save_cities_to_hdf5(cities: Cities, file_path: str):
    n_cities = len(cities)
    dt = h5py.vlen_dtype(np.dtype("int64"))
    ds = h5py.vlen_dtype(np.dtype("S15"))
    with h5py.File(file_path, "a") as f:
        cities_dset = f.create_group("cities")
        ids = []
        super_areas_list = []
        super_areas_list_lengths = []
        names = []
        commuters_list = []
        stations_list = []
        for city in cities:
            ids.append(city.id)
            names.append(city.name.encode("ascii", "ignore"))
            commuters = [person.id for person in city.commuters]
            commuters_list.append(np.array(commuters, dtype=np.int))
            stations = np.array([station.id for station in city.stations], dtype=np.int)
            stations_list.append(stations)
            super_areas = np.array(
                [
                    super_area.encode("ascii", "ignore")
                    for super_area in city.super_areas
                ],
                dtype="S20",
            )
            super_areas_list.append(super_areas)
            super_areas_list_lengths.append(len(super_areas))

        ids = np.array(ids, dtype=np.int)
        names = np.array(names, dtype="S30")
        #if len(np.unique(super_areas_list_lengths)) == 1:
            #super_areas_list = np.array(super_areas_list, dtype="S15")
        #else:
        super_areas_list = np.array(super_areas_list, dtype=ds)
        stations_list = np.array(stations_list, dtype=np.int)
        commuters_list = np.array(commuters_list, dtype=np.int)
        cities_dset.attrs["n_cities"] = n_cities
        cities_dset.create_dataset("id", data=ids)
        cities_dset.create_dataset("name", data=names)
        cities_dset.create_dataset("stations", data=stations)
        cities_dset.create_dataset("super_areas", data=super_areas_list)
        cities_dset.create_dataset("commuters", data=commuters_list)


def load_cities_from_hdf5(file_path: str):
    """
    Loads cities from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        cities = f["cities"]
        cities_list = []
        n_cities = cities.attrs["n_cities"]
        ids = cities["id"]
        names = cities["names"]
        super_areas_list = cities["super_areas"]
        cities = []
        for k in range(n_cities):
            name = names[k].decode()
            super_areas = [super_area.decode() for super_area in super_areas_list[k]]
            city = City(name=names[k].decode(), super_areas=super_areas)
            city.id = ids[k]
            cities.append(city)
    return Cities(cities)


def save_stations_to_hdf5(stations: Stations, file_path: str):
    n_hubs = len(commute_hubs)
    dt = h5py.vlen_dtype(np.dtype("int32"))
    with h5py.File(file_path, "a") as f:
        commute_hubs_dset = f.create_group("commute_hubs")
        ids = []
        cities = []
        commute_units_list = []
        commute_through_list = []
        commute_units_length_list = []
        for hub in commute_hubs:
            ids.append(hub.id)
            cities.append(hub.city)
            commute_through = []
            for commute_throu in hub.commute_through:
                commute_through.append(commute_throu.id)
            commute_through = np.array(commute_through, dtype=np.int)
            commute_through_list.append(commute_through)
            commute_units = []
            for commute_unit in hub.commuteunits:
                commute_units.append(commute_unit.id)
            commute_units_list.append(np.array(commute_units, dtype=np.int))
            commute_units_length_list.append(len(commute_units))
        if len(np.unique(commute_units_length_list)) == 1:
            commute_units_list = np.array(commute_units_list, dtype=int)
        else:
            commute_units_list = np.array(commute_units_list, dtype=dt)
        ids = np.array(ids, dtype=np.int)
        cities = np.array(cities, dtype="S20")
        commute_through_list = np.array(commute_through_list, dtype=dt)
        commute_hubs_dset.attrs["n_commute_hubs"] = n_hubs
        commute_hubs_dset.create_dataset("id", data=ids)
        commute_hubs_dset.create_dataset("city_names", data=cities)
        commute_hubs_dset.create_dataset("commute_units", data=commute_units_list)
        commute_hubs_dset.create_dataset("commute_through", data=commute_through_list)


def load_commute_hubs_from_hdf5(file_path: str):
    """
    Loads commute_hubs from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        commute_hubs = f["commute_hubs"]
        commute_hubs_list = []
        n_commute_hubs = commute_hubs.attrs["n_commute_hubs"]
        ids = commute_hubs["id"]
        city_names = commute_hubs["city_names"]
        commute_through = commute_hubs["commute_through"]
        commute_units = commute_hubs["commute_units"]
        commute_units_list = []
        for k in range(n_commute_hubs):
            commute_hub = CommuteHub(lat_lon=None, city=city_names[k].decode())
            commute_hub.id = ids[k]
            commute_hub.city = city_names[k].decode()
            commute_hub.commute_through = commute_through[k]
            for unit_id in commute_units[k]:
                cunit = CommuteUnit(
                    commutehub_id=ids[k],
                    city=city_names[k].decode(),
                    is_peak=np.random.choice(2, p=[0.8, 0.2]),
                )
                cunit.id = unit_id
                commute_units_list.append(cunit)
                commute_hub.commuteunits.append(cunit)
            commute_hubs_list.append(commute_hub)
    ch = CommuteHubs(None)
    ch.members = commute_hubs_list
    cu = CommuteUnits(ch)
    cu.members = commute_units_list
    return ch, cu


def restore_commute_properties_from_hdf5(world: World, file_path: str):
    # restore commute
    first_person_id = world.people[0].id
    first_hub_id = world.commutehubs[0].id
    # commute
    for city in world.commutecities:
        people_ids = city.people
        commute_hubs = [
            world.commutehubs[idx - first_hub_id] for idx in city.commutehubs
        ]
        city.commutehubs = commute_hubs
        commute_internal_people = [
            world.people[idx - first_person_id] for idx in city.commute_internal
        ]
        city.commute_internal = commute_internal_people

    for hub in world.commutehubs:
        commute_through_people = [
            world.people[id - first_person_id] for id in hub.commute_through
        ]
        hub.commute_through = commute_through_people
