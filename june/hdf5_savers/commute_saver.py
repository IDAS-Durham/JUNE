import h5py
import numpy as np
from june.groups.commute import (
    CommuteCity,
    CommuteCities,
    CommuteCityUnit,
    CommuteCityUnits,
    CommuteHub,
    CommuteHubs,
    CommuteUnit,
    CommuteUnits,
)

nan_integer = -999


def save_commute_cities_to_hdf5(
    commute_cities: CommuteCities, file_path: str
):
    n_cities = len(commute_cities)
    dt = h5py.vlen_dtype(np.dtype("int32"))
    with h5py.File(file_path, "a") as f:
        commute_cities_dset = f.create_group("commute_cities")
        ids = []
        commute_hubs_list = []
        commute_city_units_list = []
        cities_names_list = []
        commute_internal_list = []
        for city in commute_cities:
            ids.append(city.id)
            cities_names_list.append(city.city.encode("ascii", "ignore"))
            commute_hubs = []
            for commute_hub in city.commutehubs:
                commute_hubs.append(commute_hub.id)
            commute_hubs = np.array(commute_hubs, dtype=np.int)
            commute_hubs_list.append(commute_hubs)
            commute_internal = []
            for commute_intern in city.commute_internal:
                commute_internal.append(commute_intern.id)
            commute_internal = np.array(commute_internal, dtype=np.int)
            commute_internal_list.append(commute_internal)
            commute_city_units = []
            for commute_city_unit in city.commutecityunits:
                commute_city_units.append(commute_city_unit.id)
            commute_city_units = np.array(commute_city_units, dtype=np.int)
            commute_city_units_list.append(commute_city_units)

        ids = np.array(ids, dtype=np.int)
        cities_names_list = np.array(cities_names_list, dtype="S20")
        commute_hubs_list = np.array(commute_hubs_list, dtype=np.int)
        commute_city_units_list = np.array(commute_city_units_list, dtype=np.int)
        commute_internal_list = np.array(commute_internal_list, dtype=np.int)
        commute_cities_dset.attrs["n_commute_cities"] = n_cities
        commute_cities_dset.create_dataset("id", data=ids, maxshape=(None,))
        commute_cities_dset.create_dataset(
            "city_names", data=cities_names_list, maxshape=(None,)
        )
        commute_cities_dset.create_dataset(
            "commute_hubs", data=commute_hubs_list
        )
        commute_cities_dset.create_dataset(
            "commute_city_units", data=commute_city_units_list
        )
        commute_cities_dset.create_dataset(
            "commute_internal", data=commute_internal_list
        )


def load_commute_cities_from_hdf5(file_path: str):
    """
    Loads commute_cities from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r") as f:
        commute_cities = f["commute_cities"]
        commute_cities_list = list()
        n_commute_cities = commute_cities.attrs["n_commute_cities"]
        ids = commute_cities["id"]
        city_names = commute_cities["city_names"]
        commute_hubs = commute_cities["commute_hubs"]
        commute_city_units = commute_cities["commute_city_units"]
        commute_internal = commute_cities["commute_internal"]
        for k in range(n_commute_cities):
            commute_city = CommuteCity()
            commute_city.id = ids[k]
            commute_city.city = city_names[k].decode()
            commute_city.commute_internal = commute_internal[k]
            commute_city.commute_hubs = commute_hubs[k]
            commute_city.commute_city_units = commute_city_units[k]
            commute_cities_list.append(commute_city)
    cc = CommuteCities()
    cc.members = commute_cities_list
    return cc


def save_commute_hubs_to_hdf5(
    commute_hubs: CommuteHubs, file_path: str
):
    n_hubs = len(commute_hubs)
    dt = h5py.vlen_dtype(np.dtype("int32"))
    with h5py.File(file_path, "a") as f:
        commute_hubs_dset = f.create_group("commute_hubs")
        ids = []
        cities = []
        people_list = []
        commute_units_list = []
        for hub in commute_hubs:
            ids.append(hub.id)
            cities.append(hub.city)
            commute_units = []
            people = []
            for person in hub.people:
                people.append(person.id)
            people_list.append(np.array(people, dtype=np.int))
            for commute_unit in hub.commuteunits:
                commute_units.append(commute_unit.id)
            commute_units_list.append(np.array(commute_units, dtype=np.int))

        ids = np.array(ids, dtype=np.int)
        cities = np.array(cities, dtype="S20")
        commute_units_list = np.array(commute_units_list, dtype=np.int)
        people_list = np.array(people_list, dtype=dt)
        commute_hubs_dset.attrs["n_commute_hubs"] = n_hubs
        commute_hubs_dset.create_dataset("id", data=ids)
        commute_hubs_dset.create_dataset(
            "people", data=people_list
        )
        commute_hubs_dset.create_dataset(
            "city_names", data=cities
        )
        commute_hubs_dset.create_dataset(
            "commute_units", data=commute_units_list
        )


def load_commute_hubs_from_hdf5(file_path: str):
    """
    Loads commute_hubs from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r") as f:
        commute_hubs = f["commute_hubs"]
        commute_hubs_list = list()
        n_commute_hubs = commute_hubs.attrs["n_commute_hubs"]
        ids = commute_hubs["id"]
        people = commute_hubs["people"]
        city_names = commute_hubs["city_names"]
        commute_units = commute_hubs["commute_units"]
        for k in range(n_commute_hubs):
            commute_hub = CommuteHub(lat_lon=None, city=city_names[k].decode())
            commute_hub.id = ids[k]
            commute_hub.city = city_names[k].decode()
            for unit_id in commute_units[k]:
                cunit = CommuteUnit(
                    commutehub_id=ids[k],
                    city=city_names[k].decode(),
                    is_peak=np.random.choice(2, p = [0.8,0.2]),
                )
                cunit.id = unit_id
                commute_hub.commuteunits.append(cunit)
            commute_hub.subgroups[0]._people = [person_id for person_id in people[k]]
            commute_hubs_list.append(commute_hub)
    ch = CommuteHubs(None)
    ch.members = commute_hubs_list
    return ch

