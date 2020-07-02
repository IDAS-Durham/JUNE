import h5py
import numpy as np
from june.groups.leisure import Pub, Pubs, Grocery, Groceries, Cinema, Cinemas

nan_integer = -999

# pubs 
def save_pubs_to_hdf5(pubs: Pubs, file_path: str):
    n_pubs = len(pubs)
    with h5py.File(file_path, "a") as f:
        pubs_dset = f.create_group("pubs")
        ids = []
        coordinates = []
        for pub in pubs:
            ids.append(pub.id)
            coordinates.append(np.array(pub.coordinates, dtype=np.float))
        ids = np.array(ids, dtype=np.int)
        coordinates = np.array(coordinates, dtype=np.float)
        pubs_dset.attrs["n_pubs"] = n_pubs
        pubs_dset.create_dataset("id", data=ids)
        pubs_dset.create_dataset("coordinates", data=coordinates)


def load_pubs_from_hdf5(file_path: str):
    with h5py.File(file_path, "r") as f:
        pubs = f["pubs"]
        pubs_list = list()
        n_pubs = pubs.attrs["n_pubs"]
        ids = pubs["id"]
        coordinates = pubs["coordinates"]
        for k in range(n_pubs):
            pub = Pub()
            pub.id = ids[k]
            pub.coordinates = coordinates[k]
            pubs_list.append(pub)
    return Pubs(pubs_list)

# groceries 
def save_groceries_to_hdf5(groceries: Groceries, file_path: str):
    n_groceries = len(groceries)
    with h5py.File(file_path, "a") as f:
        groceries_dset = f.create_group("groceries")
        ids = []
        coordinates = []
        for grocery in groceries:
            ids.append(grocery.id)
            coordinates.append(np.array(grocery.coordinates, dtype=np.float))
        ids = np.array(ids, dtype=np.int)
        coordinates = np.array(coordinates, dtype=np.float)
        groceries_dset.attrs["n_groceries"] = n_groceries
        groceries_dset.create_dataset("id", data=ids)
        groceries_dset.create_dataset("coordinates", data=coordinates)


def load_groceries_from_hdf5(file_path: str):
    with h5py.File(file_path, "r") as f:
        groceries = f["groceries"]
        groceries_list = list()
        n_groceries = groceries.attrs["n_groceries"]
        ids = groceries["id"]
        coordinates = groceries["coordinates"]
        for k in range(n_groceries):
            grocery = Grocery()
            grocery.id = ids[k]
            grocery.coordinates = coordinates[k]
            groceries_list.append(grocery)
    return Groceries(groceries_list)

# cinemas

def save_cinemas_to_hdf5(cinemas: Cinemas, file_path: str):
    n_cinemas = len(cinemas)
    with h5py.File(file_path, "a") as f:
        cinemas_dset = f.create_group("cinemas")
        ids = []
        coordinates = []
        for cinema in cinemas:
            ids.append(cinema.id)
            coordinates.append(np.array(cinema.coordinates, dtype=np.float))
        ids = np.array(ids, dtype=np.int)
        coordinates = np.array(coordinates, dtype=np.float)
        cinemas_dset.attrs["n_cinemas"] = n_cinemas
        cinemas_dset.create_dataset("id", data=ids)
        cinemas_dset.create_dataset("coordinates", data=coordinates)


def load_cinemas_from_hdf5(file_path: str):
    with h5py.File(file_path, "r") as f:
        cinemas = f["cinemas"]
        cinemas_list = list()
        n_cinemas = cinemas.attrs["n_cinemas"]
        ids = cinemas["id"]
        coordinates = cinemas["coordinates"]
        for k in range(n_cinemas):
            cinema = Cinema()
            cinema.id = ids[k]
            cinema.coordinates = coordinates[k]
            cinemas_list.append(cinema)
    return Cinemas(cinemas_list)

