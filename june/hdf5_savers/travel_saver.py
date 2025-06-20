import h5py
import numpy as np
import logging

from june.groups.travel import Aircraft, Aircrafts
from june.geography import Airport, Airports
from june.epidemiology.infection.disease_config import DiseaseConfig
from june.global_context import GlobalContext
from june.world import World
from june.groups.group.make_subgroups import SubgroupParams
from .utils import read_dataset

logger = logging.getLogger("travel_saver")
nan_integer = -999

# ======= AIRPORTS FUNCTIONS =======

def save_airports_to_hdf5(
    airports: Airports, file_path: str, chunk_size: int = 50000
):
    """
    Saves the Airports object to hdf5 format file ``file_path``. For each airport,
    the following values are stored:
    - id, name, coordinates, capacity, max_concurrent_occupancy, area_id

    Parameters
    ----------
    airports
        Airports object containing a list of Airport instances
    file_path
        path of the saved hdf5 file
    chunk_size
        number of airports to save at a time
    """
    n_airports = len(airports)
    n_chunks = int(np.ceil(n_airports / chunk_size))
    with h5py.File(file_path, "a") as f:
        airports_dset = f.create_group("airports")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_airports)
            ids = []
            names = []
            capacities = []
            max_occupancies = []
            areas = []
            super_areas = []
            coordinates = []
            
            for airport in airports[idx1:idx2]:
                ids.append(airport.id)
                names.append(airport.name)
                capacities.append(airport.capacity)
                max_occupancies.append(airport.max_concurrent_occupancy)
                
                if airport.area is None:
                    areas.append(nan_integer)
                    super_areas.append(nan_integer)
                else:
                    areas.append(airport.area.id)
                    super_areas.append(airport.super_area.id if airport.super_area else nan_integer)
                
                coordinates.append(np.array(airport.coordinates))

            ids = np.array(ids, dtype=np.int64)
            names = np.array(names, dtype="S100")  # Allow for longer airport names
            capacities = np.array(capacities, dtype=np.int64)
            max_occupancies = np.array(max_occupancies, dtype=np.int64)
            areas = np.array(areas, dtype=np.int64)
            super_areas = np.array(super_areas, dtype=np.int64)
            coordinates = np.array(coordinates, dtype=np.float64)
            
            if chunk == 0:
                airports_dset.attrs["n_airports"] = n_airports
                airports_dset.create_dataset("id", data=ids, maxshape=(None,))
                airports_dset.create_dataset("name", data=names, maxshape=(None,))
                airports_dset.create_dataset("capacity", data=capacities, maxshape=(None,))
                airports_dset.create_dataset("max_occupancy", data=max_occupancies, maxshape=(None,))
                airports_dset.create_dataset("area", data=areas, maxshape=(None,))
                airports_dset.create_dataset("super_area", data=super_areas, maxshape=(None,))
                airports_dset.create_dataset(
                    "coordinates",
                    data=coordinates,
                    maxshape=(None, coordinates.shape[1]),
                )
            else:
                newshape = (airports_dset["id"].shape[0] + ids.shape[0],)
                airports_dset["id"].resize(newshape)
                airports_dset["id"][idx1:idx2] = ids
                airports_dset["name"].resize(newshape)
                airports_dset["name"][idx1:idx2] = names
                airports_dset["capacity"].resize(newshape)
                airports_dset["capacity"][idx1:idx2] = capacities
                airports_dset["max_occupancy"].resize(newshape)
                airports_dset["max_occupancy"][idx1:idx2] = max_occupancies
                airports_dset["area"].resize(newshape)
                airports_dset["area"][idx1:idx2] = areas
                airports_dset["super_area"].resize(newshape)
                airports_dset["super_area"][idx1:idx2] = super_areas
                airports_dset["coordinates"].resize(newshape[0], axis=0)
                airports_dset["coordinates"][idx1:idx2] = coordinates


def load_airports_from_hdf5(
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
    config_filename=None,
):
    """
    Loads airports from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    """
    Airport_Class = Airport
    disease_config = GlobalContext.get_disease_config()
    Airport_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        airports = f["airports"]
        airports_list = []
        n_airports = airports.attrs["n_airports"]
        n_chunks = int(np.ceil(n_airports / chunk_size))

        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_airports)
            ids = read_dataset(airports["id"], idx1, idx2)
            names = read_dataset(airports["name"], idx1, idx2)
            capacities = read_dataset(airports["capacity"], idx1, idx2)
            max_occupancies = read_dataset(airports["max_occupancy"], idx1, idx2)
            coordinates = read_dataset(airports["coordinates"], idx1, idx2)
            super_areas = read_dataset(airports["super_area"], idx1, idx2)

            for k in range(idx2 - idx1):
                super_area = super_areas[k]
                
                # Skip airports outside the domain if domain filtering is active
                if domain_super_areas is not None and super_area != nan_integer and super_area not in domain_super_areas:
                    continue
                    
                # Decode name (stored as bytes)
                name = names[k].decode() if isinstance(names[k], bytes) else names[k]
                name = name if name != "" else None
                
                # Create Airport instance
                airport = Airport_Class(
                    name=name,
                    coordinates=coordinates[k],
                    capacity=capacities[k],
                    max_concurrent_occupancy=max_occupancies[k]
                )
                airport.id = ids[k]
                airports_list.append(airport)

    # Remove ball_tree parameter from the constructor call
    return Airports(airports_list)


def restore_airport_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size=50000,
    domain_super_areas=None,
    domain_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    """
    Restores the references between airports and areas/super_areas.
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        airports = f["airports"]
        n_airports = airports.attrs["n_airports"]
        n_chunks = int(np.ceil(n_airports / chunk_size))
        
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_airports)
            length = idx2 - idx1
            
            ids = read_dataset(airports["id"], idx1, idx2)
            areas = read_dataset(airports["area"], idx1, idx2)
            super_areas = read_dataset(airports["super_area"], idx1, idx2)
            
            for k in range(length):
                # Skip if domain filtering is active and this area is not in domain
                if domain_areas is not None:
                    area = areas[k]
                    if area == nan_integer:
                        continue
                    if area not in domain_areas:
                        continue
                
                # Get airport object
                airport = world.airports.get_from_id(ids[k])
                
                # Restore area reference
                area_id = areas[k]
                if area_id != nan_integer:
                    area = world.areas.get_from_id(area_id)
                    airport.area = area
                    
                    # Add airport to area's airports list if it exists
                    if not hasattr(area, 'airports'):
                        area.airports = []
                    if airport not in area.airports:
                        area.airports.append(airport)
                
                # Restore super area reference
                super_area_id = super_areas[k]
                if super_area_id != nan_integer:
                    super_area = world.super_areas.get_from_id(super_area_id)
                    airport.super_area = super_area


# ======= AIRCRAFTS FUNCTIONS =======

def save_aircrafts_to_hdf5(
    aircrafts: Aircrafts, file_path: str, chunk_size: int = 50000
):
    """
    Saves the Aircrafts object to hdf5 format file ``file_path``. For each aircraft,
    the following values are stored:
    - id, flight_duration, num_seats, capacity, occupied_seats, airport_id

    Parameters
    ----------
    aircrafts
        Aircrafts object containing a list of Aircraft instances
    file_path
        path of the saved hdf5 file
    chunk_size
        number of aircrafts to save at a time
    """
    n_aircrafts = len(aircrafts)
    n_chunks = int(np.ceil(n_aircrafts / chunk_size))
    with h5py.File(file_path, "a") as f:
        aircrafts_dset = f.create_group("aircrafts")
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_aircrafts)
            ids = []
            flight_durations = []
            num_seats = []
            capacities = []
            occupied_seats = []
            airport_ids = []
            
            for aircraft in aircrafts[idx1:idx2]:
                ids.append(aircraft.id)
                flight_durations.append(aircraft.flight_duration)
                num_seats.append(aircraft.num_seats)
                capacities.append(aircraft.capacity)
                occupied_seats.append(aircraft._occupied_seats)
                
                if aircraft.airport is None:
                    airport_ids.append(nan_integer)
                else:
                    airport_ids.append(aircraft.airport.id)

            ids = np.array(ids, dtype=np.int64)
            flight_durations = np.array(flight_durations, dtype=np.float64)
            num_seats = np.array(num_seats, dtype=np.int64)
            capacities = np.array(capacities, dtype=np.int64)
            occupied_seats = np.array(occupied_seats, dtype=np.int64)
            airport_ids = np.array(airport_ids, dtype=np.int64)
            
            if chunk == 0:
                aircrafts_dset.attrs["n_aircrafts"] = n_aircrafts
                aircrafts_dset.create_dataset("id", data=ids, maxshape=(None,))
                aircrafts_dset.create_dataset("flight_duration", data=flight_durations, maxshape=(None,))
                aircrafts_dset.create_dataset("num_seats", data=num_seats, maxshape=(None,))
                aircrafts_dset.create_dataset("capacity", data=capacities, maxshape=(None,))
                aircrafts_dset.create_dataset("occupied_seats", data=occupied_seats, maxshape=(None,))
                aircrafts_dset.create_dataset("airport_id", data=airport_ids, maxshape=(None,))
            else:
                newshape = (aircrafts_dset["id"].shape[0] + ids.shape[0],)
                aircrafts_dset["id"].resize(newshape)
                aircrafts_dset["id"][idx1:idx2] = ids
                aircrafts_dset["flight_duration"].resize(newshape)
                aircrafts_dset["flight_duration"][idx1:idx2] = flight_durations
                aircrafts_dset["num_seats"].resize(newshape)
                aircrafts_dset["num_seats"][idx1:idx2] = num_seats
                aircrafts_dset["capacity"].resize(newshape)
                aircrafts_dset["capacity"][idx1:idx2] = capacities
                aircrafts_dset["occupied_seats"].resize(newshape)
                aircrafts_dset["occupied_seats"][idx1:idx2] = occupied_seats
                aircrafts_dset["airport_id"].resize(newshape)
                aircrafts_dset["airport_id"][idx1:idx2] = airport_ids


def load_aircrafts_from_hdf5(
    file_path: str,
    chunk_size=50000,
    config_filename=None,
):
    """
    Loads aircrafts from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    """
    Aircraft_Class = Aircraft
    disease_config = GlobalContext.get_disease_config()
    Aircraft_Class.subgroup_params = SubgroupParams.from_disease_config(disease_config)

    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        aircrafts = f["aircrafts"]
        aircrafts_list = []
        n_aircrafts = aircrafts.attrs["n_aircrafts"]
        n_chunks = int(np.ceil(n_aircrafts / chunk_size))

        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_aircrafts)
            ids = read_dataset(aircrafts["id"], idx1, idx2)
            flight_durations = read_dataset(aircrafts["flight_duration"], idx1, idx2)
            num_seats = read_dataset(aircrafts["num_seats"], idx1, idx2)
            capacities = read_dataset(aircrafts["capacity"], idx1, idx2)
            occupied_seats = read_dataset(aircrafts["occupied_seats"], idx1, idx2)

            for k in range(idx2 - idx1):
                # Create Aircraft instance
                aircraft = Aircraft_Class(
                    flight_duration=flight_durations[k]
                )
                aircraft.id = ids[k]
                aircraft.num_seats = num_seats[k]
                aircraft.capacity = capacities[k]
                aircraft._occupied_seats = occupied_seats[k]
                
                aircrafts_list.append(aircraft)

    return Aircrafts(aircrafts_list)


def restore_aircraft_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size=50000,
):
    """
    Restores the references between aircrafts and airports.
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        aircrafts = f["aircrafts"]
        n_aircrafts = aircrafts.attrs["n_aircrafts"]
        n_chunks = int(np.ceil(n_aircrafts / chunk_size))
        
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_aircrafts)
            length = idx2 - idx1
            
            ids = read_dataset(aircrafts["id"], idx1, idx2)
            airport_ids = read_dataset(aircrafts["airport_id"], idx1, idx2)
            
            for k in range(length):
                # Get aircraft object
                aircraft = world.aircrafts.get_from_id(ids[k])
                
                # Restore airport reference
                airport_id = airport_ids[k]
                if airport_id != nan_integer:
                    try:
                        airport = world.airports.get_from_id(airport_id)
                        aircraft.airport = airport
                    except (AttributeError, KeyError) as e:
                        logger.warning(f"Could not restore airport {airport_id} for aircraft {ids[k]}: {e}")