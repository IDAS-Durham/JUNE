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
    ds30 = h5py.vlen_dtype(np.dtype("S30"))
    with h5py.File(file_path, "a") as f:
        cities_dset = f.create_group("cities")
        ids = []
        super_areas_list = []
        super_areas_list_lengths = []
        names = []
        commuters_list = []
        commuters_list_lengths = []
        stations_id_list = []
        station_ids_lengths = []
        stations_per_city = []
        cities_transport_numbers = []
        coordinates = []
        for city in cities:
            ids.append(city.id)
            names.append(city.name.encode("ascii", "ignore"))
            commuters = [person_id for person_id in list(city.commuter_ids)]
            commuters_list_lengths.append(len(commuters))
            commuters_list.append(np.array(commuters, dtype=np.int))
            super_areas = np.array(
                [
                    super_area.encode("ascii", "ignore")
                    for super_area in city.super_areas
                ],
                dtype="S20",
            )
            super_areas_list.append(super_areas)
            super_areas_list_lengths.append(len(super_areas))
            coordinates.append(np.array(city.coordinates, dtype=np.float))
            cities_transport_numbers.append(len(city.city_transports))
            # stations
            stations_per_city.append(len(city.stations))
            stations_ids = np.array(
                [station.id for station in city.stations], dtype=np.int
            )
            station_ids_lengths.append(len(stations_ids))
            stations_id_list.append(stations_ids)

        ids = np.array(ids, dtype=np.int)
        names = np.array(names, dtype="S30")
        if len(np.unique(super_areas_list_lengths)) == 1:
            super_areas_list = np.array(super_areas_list, dtype="S15")
        else:
            super_areas_list = np.array(super_areas_list, dtype=ds)
        if len(np.unique(station_ids_lengths)) == 1:
            stations_id_list = np.array(stations_id_list, dtype=np.int)
        else:
            stations_id_list = np.array(stations_id_list, dtype=dt)
        if len(np.unique(commuters_list_lengths)) == 1:
            commuters_list = np.array(commuters_list, dtype=np.int)
        else:
            commuters_list = np.array(commuters_list, dtype=dt)
        cities_transport_numbers = np.array(cities_transport_numbers, dtype=np.int)

        stations_ids = np.array(stations_ids, dtype=dt)
        stations_per_city = np.array(stations_per_city, dtype=np.int)

        cities_dset.attrs["n_cities"] = n_cities
        cities_dset.create_dataset("id", data=ids)
        cities_dset.create_dataset("name", data=names)
        cities_dset.create_dataset("coordinates", data=coordinates)
        cities_dset.create_dataset("super_areas", data=super_areas_list)
        cities_dset.create_dataset("commuters", data=commuters_list)
        cities_dset.create_dataset(
            "city_transports_number", data=cities_transport_numbers
        )
        # stations
        cities_dset.create_dataset("station_id", data=stations_id_list)
        cities_dset.create_dataset("stations_per_city", data=stations_per_city)


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
        names = cities["name"]
        coordinates = cities["coordinates"]
        super_areas_list = cities["super_areas"]
        city_transports_list = cities["city_transports_number"]

        station_ids_list = cities["station_id"]
        stations_per_city = cities["stations_per_city"]
        cities = []
        city_transports = []
        for k in range(n_cities):
            name = names[k].decode()
            super_areas = [super_area.decode() for super_area in super_areas_list[k]]
            city = City(
                name=names[k].decode(),
                super_areas=super_areas,
                coordinates=coordinates[k],
            )
            city_transports_city = []
            for i in range(city_transports_list[k]):
                city_transports_city.append(CityTransport())
            city.city_transports = CityTransports(city_transports_city)
            city_transports += city_transports_city
            city.id = ids[k]
            cities.append(city)
    return Cities(cities), CityTransports(city_transports)


def save_stations_to_hdf5(stations: Stations, file_path: str):
    n_stations = len(stations)
    dt = h5py.vlen_dtype(np.dtype("int64"))
    ds = h5py.vlen_dtype(np.dtype("S15"))
    ds30 = h5py.vlen_dtype(np.dtype("S30"))
    with h5py.File(file_path, "a") as f:
        stations_dset = f.create_group("stations")
        stations_dset.attrs["n_stations"] = n_stations
        station_ids = []
        station_cities = []
        station_super_areas = []
        station_commuters = []
        station_transport_numbers = []
        for station in stations:
            station_ids.append(station.id)
            station_super_areas.append(station.super_area.id)
            station_commuters.append(
                np.array([person_id for person_id in list(station.commuter_ids)], dtype=np.int)
            )
            station_transport_numbers.append(len(station.inter_city_transports))
            station_cities.append(station.city.encode("ascii", "ignore"))
        station_ids = np.array(station_ids, dtype=np.int)
        station_super_areas = np.array(station_super_areas, dtype=np.int)
        station_commuters = np.array(station_commuters, dtype=dt)
        station_transport_numbers = np.array(station_transport_numbers, dtype=np.int)
        station_cities = np.array(station_cities, dtype="S30")
        stations_dset.create_dataset("id", data=station_ids)
        stations_dset.create_dataset("super_area", data=station_super_areas)
        stations_dset.create_dataset("commuters", data=station_commuters)
        stations_dset.create_dataset(
            "transport_numbers", data=station_transport_numbers
        )
        stations_dset.create_dataset("station_cities", data=station_cities)


def load_stations_from_hdf5(file_path: str):
    """
    Loads cities from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        stations = f["stations"]
        n_stations = stations.attrs["n_stations"]
        ids = stations["id"]
        transport_numbers = stations["transport_numbers"]
        cities = stations["station_cities"]
        stations = []
        inter_city_transports = []
        for k in range(n_stations):
            station = Station(city=cities[k].decode())
            station.id = ids[k]
            stations.append(station)
            inter_city_transports_station = []
            for i in range(transport_numbers[k]):
                inter_city_transports_station.append(InterCityTransport())
                station.inter_city_transports = inter_city_transports_station
            inter_city_transports += inter_city_transports_station
    return Stations(stations), InterCityTransports(inter_city_transports)


def restore_cities_and_stations_properties_from_hdf5(world: World, file_path: str):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        first_city_id = world.cities[0].id
        first_person_id = world.people[0].id
        first_station_id = world.stations[0].id
        first_super_area_id = world.super_areas[0].id
        cities = f["cities"]
        stations = f["stations"]
        stations_per_city = cities["stations_per_city"]
        n_cities = cities.attrs["n_cities"]
        n_stations = stations.attrs["n_stations"]
        city_ids = cities["id"]
        city_station_ids = cities["station_id"]
        city_commuters_list = cities["commuters"]
        station_ids = stations["id"]
        station_commuters_list = stations["commuters"]
        station_super_areas = stations["super_area"]
        for k in range(n_stations):
            station_id = station_ids[k]
            station = world.stations[station_id - first_station_id]
            station.super_area = world.super_areas[
                station_super_areas[k] - first_super_area_id
            ]
            station.commuter_ids = set([
                c_id 
                for c_id in station_commuters_list[k]
            ])

        for k in range(n_cities):
            city_id = city_ids[k]
            city = world.cities[city_id - first_city_id]
            commuters = set([
                commuter_id 
                for commuter_id in city_commuters_list[k]
            ])
            city.commuter_ids = commuters
            city.stations = []
            for station_id in city_station_ids[k]:
                station = world.stations[station_id - first_station_id]
                city.stations.append(station)
