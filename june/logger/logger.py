import h5py
import numpy as np
from june.demography import Population, Person
from pathlib import Path


class Logger:
    def __init__(self, save_path: str = "results", file_name: str = "logger.hdf5"):

        self.save_path = save_path
        self.file_path = Path(self.save_path) / file_name
        # Remove if exists

    def log_population(self, population: Population, chunk_size: int = 100000):
        """
        Saves the Population object to hdf5 format file ``self.save_path``. Currently for each person,
        the following values are stored:
        - id, age, sex, super_area

        Parameters
        ----------
        population
            population object
        chunk_size
            number of people to save at a time. Note that they have to be copied to be saved,
            so keep the number below 1e6.
        """
        n_people = len(population.people)
        dt = h5py.vlen_dtype(np.dtype("int32"))
        # dt = tuple
        n_chunks = int(np.ceil(n_people / chunk_size))
        with h5py.File(self.file_path, "a") as f:
            people_dset = f.create_group("population")
            for chunk in range(n_chunks):
                idx1 = chunk * chunk_size
                idx2 = min((chunk + 1) * chunk_size, n_people)
                ids = []
                ages = []
                sexes = []
                super_areas = []

                for person in population.people[idx1:idx2]:
                    ids.append(person.id)
                    ages.append(person.age)
                    sexes.append(person.sex.encode("ascii", "ignore"))
                    if person.area.super_area is not None:
                        super_areas.append(person.area.super_area.name)
                    else:
                        super_areas.append(nan_integer)

                ids = np.array(ids, dtype=np.int)
                ages = np.array(ages, dtype=np.int)
                sexes = np.array(sexes, dtype="S10")
                super_areas = np.array(super_areas, dtype="S10")

                if chunk == 0:
                    people_dset.attrs["n_people"] = n_people
                    people_dset.create_dataset("id", data=ids, maxshape=(None,))
                    people_dset.create_dataset("age", data=ages, maxshape=(None,))
                    people_dset.create_dataset("sex", data=sexes, maxshape=(None,))
                    people_dset.create_dataset(
                        "super_area", data=super_areas, maxshape=(None,)
                    )
                else:
                    newshape = (people_dset["id"].shape[0] + ids.shape[0],)
                    people_dset["id"].resize(newshape)
                    people_dset["id"][idx1:idx2] = ids
                    people_dset["age"].resize(newshape)
                    people_dset["age"][idx1:idx2] = ages
                    people_dset["sex"].resize(newshape)
                    people_dset["sex"][idx1:idx2] = sexes
                    people_dset["super_area"].resize(newshape)
                    people_dset["super_area"][idx1:idx2] = super_areas

    def log_infected(self, date, infected_people, symptoms):
        # TODO: might have to do in chunks ?
        time_stamp = date.strftime("%Y-%m-%dT%H:%M:%S.%f")
        with h5py.File(self.file_path, "a") as f:
            infected_dset = f.create_group(time_stamp)
            ids = []
            for person in infected_people:
                ids.append(person.id)

            ids = np.array(ids, dtype=np.int)
            symptoms = np.array(symptoms, dtype=np.int)
            infected_dset["id"] = ids
            infected_dset["symptoms"] = symptoms
