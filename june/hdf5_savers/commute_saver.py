import h5py
import numpy as np

from june.world import World
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


def save_commute_cities_to_hdf5(commute_cities: CommuteCities, file_path: str):
    n_cities = len(commute_cities)
    dt = h5py.vlen_dtype(np.dtype("int64"))
    with h5py.File(file_path, "a") as f:
        commute_cities_dset = f.create_group("commute_cities")
        ids = []
        commute_hubs_list = []
        commute_city_units_ids_list = []
        commute_city_units_is_peak_list = []
        cities_names_list = []
        commute_internal_list = []
        for city in commute_cities:
            ids.append(city.id)
            cities_names_list.append(city.city.encode("ascii", "ignore"))
            if not city.commutehubs:
                hubs = np.array([-999, -999], dtype=np.int)
            else:
                hubs = np.array([hub.id for hub in city.commutehubs], dtype=np.int)
            commute_hubs_list.append(hubs)
            commute_internal = []
            for commute_intern in city.commute_internal:
                commute_internal.append(commute_intern.id)
            commute_internal = np.array(commute_internal, dtype=np.int)
            commute_internal_list.append(commute_internal)
            commute_city_units_ids = []
            commute_city_units_is_peak = []
            for commute_city_unit in city.commutecityunits:
                commute_city_units_ids.append(commute_city_unit.id)
                commute_city_units_is_peak.append(commute_city_unit.is_peak)
            commute_city_units_ids = np.array(commute_city_units_ids, dtype=np.int)
            commute_city_units_is_peak = np.array(
                commute_city_units_is_peak, dtype=np.int
            )
            commute_city_units_ids_list.append(commute_city_units_ids)
            commute_city_units_is_peak_list.append(commute_city_units_is_peak)

        ids = np.array(ids, dtype=np.int)
        cities_names_list = np.array(cities_names_list, dtype="S20")
        commute_city_units_ids_list = np.array(commute_city_units_ids_list, dtype=dt)
        commute_city_units_is_peak_list = np.array(
            commute_city_units_is_peak_list, dtype=dt
        )
        commute_internal_list = np.array(commute_internal_list, dtype=dt)
        commute_cities_dset.attrs["n_commute_cities"] = n_cities
        commute_cities_dset.create_dataset("id", data=ids)
        commute_cities_dset.create_dataset("city_names", data=cities_names_list)
        try:
            commute_hubs_list = np.array(commute_hubs_list, dtype=dt)
            commute_cities_dset.create_dataset("commute_hubs", data=commute_hubs_list)
        except:
            commute_hubs_list = np.array(commute_hubs_list,dtype=np.int)
            commute_cities_dset.create_dataset("commute_hubs", data=commute_hubs_list)
        commute_cities_dset.create_dataset(
            "commute_city_units_ids", data=commute_city_units_ids_list
        )
        commute_cities_dset.create_dataset(
            "commute_city_units_is_peak", data=commute_city_units_is_peak_list
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
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        commute_cities = f["commute_cities"]
        commute_cities_list = []
        n_commute_cities = commute_cities.attrs["n_commute_cities"]
        ids = commute_cities["id"]
        city_names = commute_cities["city_names"]
        commute_hubs = commute_cities["commute_hubs"]
        commute_city_units_ids_list = commute_cities["commute_city_units_ids"]
        commute_city_units_is_peak_list = commute_cities["commute_city_units_is_peak"]
        commute_internal = commute_cities["commute_internal"]
        commute_city_units_list = []
        for k in range(n_commute_cities):
            commute_city = CommuteCity()
            commute_city.id = ids[k]
            commute_city.city = city_names[k].decode()
            if commute_hubs[k][0] == -999:
                commute_city.commutehubs = []
            else:
                commute_city.commutehubs = commute_hubs[k]
            commute_city.commute_internal = commute_internal[k]
            commute_city_units_ids = commute_city_units_ids_list[k]
            commute_city_units_is_peak = commute_city_units_is_peak_list[k]
            for i in range(len(commute_city_units_ids)):
                cu = CommuteCityUnit(
                    city=commute_city.city, is_peak=commute_city_units_is_peak[i]
                )
                cu.id = commute_city_units_ids[i]
                commute_city.commutecityunits.append(cu)
                commute_city_units_list.append(cu)
            commute_cities_list.append(commute_city)
    cc = CommuteCities(commute_cities_list)
    ccu = CommuteCityUnits(cc)
    ccu.members = commute_city_units_list
    return cc, ccu


def save_commute_hubs_to_hdf5(commute_hubs: CommuteHubs, file_path: str):
    n_hubs = len(commute_hubs)
    dt = h5py.vlen_dtype(np.dtype("int32"))
    with h5py.File(file_path, "a") as f:
        commute_hubs_dset = f.create_group("commute_hubs")
        ids = []
        cities = []
        commute_units_list = []
        commute_through_list = []
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

        ids = np.array(ids, dtype=np.int)
        cities = np.array(cities, dtype="S20")
        commute_through_list = np.array(commute_through_list, dtype=dt)
        commute_units_list = np.array(commute_units_list, dtype=dt)
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
        commute_hubs = [
            world.commutehubs[idx - first_hub_id] for idx in city.commutehubs
        ]
        city.commutehubs = commute_hubs
        commute_internal_people = [
            world.people[idx - first_person_id] for idx in city.commute_internal
        ]
        city.commute_internal = commute_internal_people
