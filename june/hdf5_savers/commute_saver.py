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
int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
string_15_vlen_type = h5py.vlen_dtype(np.dtype("S15"))
string_30_vlen_type = h5py.vlen_dtype(np.dtype("S30"))

def save_cities_to_hdf5(cities: Cities, file_path: str):
    n_cities = len(cities)
    with h5py.File(file_path, "a") as f:
        cities_dset = f.create_group("cities")
        ids = []
        super_areas_list = []
        city_super_area_list = []
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
            if city.super_area is None:
                city_super_area_list.append(nan_integer)
            else:
                city_super_area_list.append(city.super_area.id)
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
            super_areas_list = np.array(super_areas_list, dtype=string_15_vlen_type)
        if len(np.unique(station_ids_lengths)) == 1:
            stations_id_list = np.array(stations_id_list, dtype=np.int)
        else:
            stations_id_list = np.array(stations_id_list, dtype=int_vlen_type)
        if len(np.unique(commuters_list_lengths)) == 1:
            commuters_list = np.array(commuters_list, dtype=np.int)
        else:
            commuters_list = np.array(commuters_list, dtype=int_vlen_type)
        cities_transport_numbers = np.array(cities_transport_numbers, dtype=np.int)
        city_super_area_list = np.array(city_super_area_list, dtype=np.int)

        stations_ids = np.array(stations_ids, dtype=int_vlen_type)
        stations_per_city = np.array(stations_per_city, dtype=np.int)

        cities_dset.attrs["n_cities"] = n_cities
        cities_dset.create_dataset("id", data=ids)
        cities_dset.create_dataset("name", data=names)
        cities_dset.create_dataset("coordinates", data=coordinates)
        cities_dset.create_dataset("super_areas", data=super_areas_list)
        cities_dset.create_dataset("city_super_area", data=city_super_area_list)
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
        length = n_cities
        idx1 = 0
        idx2 = length
        ids = np.empty(length, dtype=int)
        cities["id"].read_direct(
            cities, np.s_[idx1:idx2], np.s_[0:length]
        )
        names = np.empty(length, dtype="S30")
        cities["name"].read_direct(
            names, np.s_[idx1:idx2], np.s_[0:length]
        )
        coordinates = np.empty((length,2), dtype=float)
        cities["coordinates"].read_direct(
            coordinates, np.s_[idx1:idx2], np.s_[0:length]
        )
        super_areas_list = np.empty(length, dtype="S20")
        cities["super_areas"].read_direct(
            super_areas_list, np.s_[idx1:idx2], np.s_[0:length]
        )
        city_transports_list = np.empty(length, dtype=int)
        cities["city_transports_number"].read_direct(
            city_transports_list, np.s_[idx1:idx2], np.s_[0:length]
        )
        station_ids_list = np.empty(length, dtype=int)
        cities["station_id"].read_direct(
            station_ids_list, np.s_[idx1:idx2], np.s_[0:length]
        )
        stations_per_city = np.empty(length, dtype=int)
        cities["stations_per_city"].read_direct(
            stations_per_city, np.s_[idx1:idx2], np.s_[0:length]
        )
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
        station_commuters = np.array(station_commuters, dtype=int_vlen_type)
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
        length = n_stations
        idx1 = 0
        idx2 = length
        ids = np.empty(length, dtype=int)
        cities["id"].read_direct(
            ids, np.s_[idx1:idx2], np.s_[0:length]
        )
        transport_numbers = np.empty(length, dtype=int)
        cities["transport_numbers"].read_direct(
            transport_numbers, np.s_[idx1:idx2], np.s_[0:length]
        )
        cities = np.empty(length, dtype="S30")
        cities["station_cities"].read_direct(
            cities, np.s_[idx1:idx2], np.s_[0:length]
        )
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
        #load cities data
        cities = f["cities"]
        n_cities = cities.attrs["n_cities"]
        stations_per_city= np.empty(n_cities, dtype=int)
        cities["stations_per_city"].read_direct(
            stations_per_city, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        city_ids = np.empty(n_cities, dtype=int)
        cities["id"].read_direct(
            city_ids, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        city_station_ids = np.empty(n_cities, dtype=int_vlen_type)
        cities["station_id"].read_direct(
            city_station_ids, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        city_commuters_list = np.empty(n_cities, dtype=int_vlen_type)
        cities["commuters"].read_direct(
            city_commuters_list, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        # load stations data
        stations = f["stations"]
        n_stations = stations.attrs["n_stations"]
        station_ids = np.empty(n_stations, dtype=int)
        stations["id"].read_direct(
            station_ids, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        station_commuters_list = np.empty(n_stations, dtype=int_vlen_type)
        stations["commuters"].read_direct(
            station_commuters_list, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        station_super_areas = np.empty(n_stations, dtype=int)
        stations["super_area"].read_direct(
            station_super_areas, np.s_[0:n_cities], np.s_[0:n_cities]
        )
        for k in range(n_stations):
            station_id = station_ids[k]
            station = world.stations.get_from_id(station_id)
            station.super_area = world.super_areas.get_from_id(station_super_areas[k])
            station.commuter_ids = set([
                c_id 
                for c_id in station_commuters_list[k]
            ])

        for k in range(n_cities):
            city_id = city_ids[k]
            city = world.cities.get_from_id(city_id)
            commuters = set([
                commuter_id 
                for commuter_id in city_commuters_list[k]
            ])
            city.commuter_ids = commuters
            city.stations = []
            for station_id in city_station_ids[k]:
                station = world.stations.get_from_id(station_id)
                city.stations.append(station)
