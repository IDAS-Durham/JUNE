import h5py
import numpy as np
from typing import List

from june.world import World
from june.geography import (
    City,
    Cities,
    Station,
    Stations,
    ExternalStation,
    ExternalCity,
)
from .utils import read_dataset
from june.groups import ExternalGroup, ExternalSubgroup
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
        city_super_area_list = []
        super_areas_list = []
        super_areas_list_lengths = []
        names = []
        commuters_list = []
        commuters_list_lengths = []
        stations_id_list = []
        station_ids_lengths = []
        city_transport_ids_list = []
        city_transport_ids_list_lengths = []
        coordinates = []
        super_area_city = []
        super_area_closest_commuting_city = []
        super_area_closest_commuting_city_super_area = []
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
            city_transport_ids = [
                city_transport.id for city_transport in city.city_transports
            ]
            city_transport_ids_list.append(np.array(city_transport_ids, dtype=np.int))
            city_transport_ids_list_lengths.append(len(city_transport_ids))
            if city.super_area is None:
                city_super_area_list.append(nan_integer)
            else:
                city_super_area_list.append(city.super_area.id)
            # stations
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
        if len(np.unique(city_transport_ids_list_lengths)) == 1:
            city_transport_ids_list = np.array(city_transport_ids_list, dtype=np.int)
        else:
            city_transport_ids_list = np.array(
                city_transport_ids_list, dtype=int_vlen_type
            )
        city_super_area_list = np.array(city_super_area_list, dtype=np.int)

        stations_ids = np.array(stations_ids, dtype=int_vlen_type)

        cities_dset.attrs["n_cities"] = n_cities
        cities_dset.create_dataset("id", data=ids)
        cities_dset.create_dataset("name", data=names)
        cities_dset.create_dataset("coordinates", data=coordinates)
        cities_dset.create_dataset("super_areas", data=super_areas_list)
        cities_dset.create_dataset("city_super_area", data=city_super_area_list)
        cities_dset.create_dataset("commuters", data=commuters_list)
        cities_dset.create_dataset("city_transport_ids", data=city_transport_ids_list)
        # stations
        cities_dset.create_dataset("station_id", data=stations_id_list)


def load_cities_from_hdf5(
    file_path: str,
    domain_super_areas: List[int] = None,
    super_areas_to_domain_dict: dict = None,
):
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
        ids = read_dataset(cities["id"])
        names = read_dataset(cities["name"])
        coordinates = read_dataset(cities["coordinates"])
        super_areas_list = read_dataset(cities["super_areas"])
        city_super_areas = read_dataset(cities["city_super_area"])
        city_transport_ids_list = read_dataset(cities["city_transport_ids"])
        cities = []
        city_transports = []
        for k in range(n_cities):
            name = names[k].decode()
            super_areas = [super_area.decode() for super_area in super_areas_list[k]]
            city_super_area = city_super_areas[k]
            city_transport_ids = city_transport_ids_list[k]
            city_transports_city = []
            if domain_super_areas is None or city_super_area in domain_super_areas:
                city = City(
                    name=names[k].decode(),
                    super_areas=super_areas,
                    coordinates=coordinates[k],
                )
                city.id = ids[k]
                for city_transport_id in city_transport_ids:
                    city_transport = CityTransport()
                    city_transport.id = city_transport_id
                    city_transports_city.append(city_transport)
            else:
                # this city is external to the domain
                city = ExternalCity(
                    id=ids[k],
                    domain_id=super_areas_to_domain_dict[city_super_area],
                    commuter_ids=None,
                    name = names[k].decode()
                )
                for city_transport_id in city_transport_ids:
                    city_transport = ExternalGroup(
                        domain_id=super_areas_to_domain_dict[city_super_area],
                        spec="city_transport",
                        id=city_transport_id,
                    )
                    city_transports_city.append(city_transport)
            city.city_transports = CityTransports(city_transports_city)
            city_transports += city_transports_city
            cities.append(city)
    return Cities(cities, ball_tree=False), CityTransports(city_transports)


def save_stations_to_hdf5(stations: Stations, file_path: str):
    n_stations = len(stations)
    with h5py.File(file_path, "a") as f:
        stations_dset = f.create_group("stations")
        stations_dset.attrs["n_stations"] = n_stations
        station_ids = []
        station_cities = []
        station_super_areas = []
        station_commuters = []
        station_transport_ids_list = []
        station_transport_ids_list_lengths = []
        for station in stations:
            station_ids.append(station.id)
            station_super_areas.append(station.super_area.id)
            station_commuters.append(
                np.array(
                    [person_id for person_id in list(station.commuter_ids)],
                    dtype=np.int,
                )
            )
            station_transport_ids = [
                transport.id for transport in station.inter_city_transports
            ]
            station_transport_ids_list.append(
                np.array(station_transport_ids, dtype=np.int)
            )
            station_transport_ids_list_lengths.append(len(station_transport_ids))
            station_cities.append(station.city.encode("ascii", "ignore"))
        station_ids = np.array(station_ids, dtype=np.int)
        station_super_areas = np.array(station_super_areas, dtype=np.int)
        station_commuters = np.array(station_commuters, dtype=int_vlen_type)
        station_cities = np.array(station_cities, dtype="S30")
        if len(np.unique(station_transport_ids_list_lengths)) == 1:
            station_transport_ids_list = np.array(
                station_transport_ids_list, dtype=np.int
            )
        else:
            station_transport_ids_list = np.array(
                station_transport_ids_list, dtype=int_vlen_type
            )
        stations_dset.create_dataset("id", data=station_ids)
        stations_dset.create_dataset("super_area", data=station_super_areas)
        stations_dset.create_dataset("commuters", data=station_commuters)
        stations_dset.create_dataset("transport_ids", data=station_transport_ids_list)
        stations_dset.create_dataset("station_cities", data=station_cities)


def load_stations_from_hdf5(
    file_path: str,
    domain_super_areas: List[int] = None,
    super_areas_to_domain_dict: dict = None,
):
    """
    Loads cities from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        stations = f["stations"]
        n_stations = stations.attrs["n_stations"]
        ids = read_dataset(stations["id"])
        if len(stations["transport_ids"].shape) == 1:
            transport_ids = read_dataset(stations["transport_ids"])
        else:
            transport_ids = [[] for _ in range(stations["transport_ids"].len())]
        cities = read_dataset(stations["station_cities"])
        super_areas = read_dataset(stations["super_area"])
        stations = []
        inter_city_transports = []
        for k in range(n_stations):
            super_area = super_areas[k]
            inter_city_transports_station = []
            if domain_super_areas is None or super_area in domain_super_areas:
                station = Station(city=cities[k].decode())
                station.id = ids[k]
                for transport_id in transport_ids[k]:
                    inter_city_transport = InterCityTransport()
                    inter_city_transport.id = transport_id
                    inter_city_transports_station.append(inter_city_transport)
            else:
                station = ExternalStation(
                    id=ids[k],
                    domain_id=super_areas_to_domain_dict[super_area],
                    commuter_ids=None,
                )
                for transport_id in transport_ids[k]:
                    inter_city_transport = ExternalGroup(
                        domain_id=super_areas_to_domain_dict[super_area],
                        spec="inter_city_transport",
                        id=transport_id,
                    )
                    inter_city_transports_station.append(inter_city_transport)
            station.inter_city_transports = inter_city_transports_station
            inter_city_transports += inter_city_transports_station
            stations.append(station)
    return Stations(stations), InterCityTransports(inter_city_transports)


def restore_cities_and_stations_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size: int,
    domain_super_areas: List[int] = None,
    super_areas_to_domain_dict: dict = None,
):
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        # load cities data
        cities = f["cities"]
        n_cities = cities.attrs["n_cities"]
        city_ids = read_dataset(cities["id"])
        city_station_ids = read_dataset(cities["station_id"])
        city_commuters_list = read_dataset(cities["commuters"])
        city_super_areas = read_dataset(cities["city_super_area"])
        # load stations data
        stations = f["stations"]
        n_stations = stations.attrs["n_stations"]
        station_ids = read_dataset(stations["id"])
        station_super_areas = read_dataset(stations["super_area"])
        if len(stations["commuters"].shape) == 1:
            station_commuters_list = read_dataset(stations["commuters"])
        else:
            station_commuters_list = [[] for _ in range(stations["commuters"].len())]
        for k in range(n_stations):
            station_id = station_ids[k]
            station = world.stations.get_from_id(station_id)
            station.commuter_ids = set([c_id for c_id in station_commuters_list[k]])
            station_super_area = station_super_areas[k]
            if domain_super_areas is None or station_super_area in domain_super_areas:
                station.super_area = world.super_areas.get_from_id(
                    station_super_areas[k]
                )

        for k in range(n_cities):
            city_id = city_ids[k]
            city_super_area = city_super_areas[k]
            city = world.cities.get_from_id(city_id)
            commuters = set([commuter_id for commuter_id in city_commuters_list[k]])
            city.commuter_ids = commuters
            if domain_super_areas is None or city_super_area in domain_super_areas:
                city.stations = []
                city_super_area_instance = world.super_areas.get_from_id(
                    city_super_area
                )
                city.super_area = city_super_area_instance
                city_super_area_instance.city = city
                for station_id in city_station_ids[k]:
                    station = world.stations.get_from_id(station_id)
                    city.stations.append(station)
        # super areas info
        geography = f["geography"]
        n_super_areas = geography.attrs["n_super_areas"]
        n_chunks = int(np.ceil(n_super_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_super_areas)
            length = idx2 - idx1
            super_area_ids = read_dataset(geography["super_area_id"], idx1, idx2)
            super_area_city = read_dataset(geography["super_area_city"], idx1, idx2)
            super_area_closest_stations_cities = read_dataset(
                geography["super_area_closest_stations_cities"], idx1, idx2
            )
            super_area_closest_stations_stations = read_dataset(
                geography["super_area_closest_stations_stations"], idx1, idx2
            )
            # load closest station
            for k in range(length):
                super_area_id = super_area_ids[k]
                if domain_super_areas is not None:
                    if super_area_id == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area_id not in domain_super_areas:
                        continue
                super_area = world.super_areas.get_from_id(super_area_id)
                if super_area_city[k] == nan_integer:
                    super_area.city = None
                else:
                    super_area.city = world.cities.get_from_id(super_area_city[k])
                for city, station in zip(
                    super_area_closest_stations_cities[k],
                    super_area_closest_stations_stations[k],
                ):
                    super_area.closest_station_for_city[
                        city.decode()
                    ] = world.stations.get_from_id(station)
