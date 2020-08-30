import h5py
import os
import numpy as np
from typing import List
from june.demography import Population
from collections import defaultdict
from pathlib import Path
import datetime


class Logger:
    def __init__(self, save_path: str = "results"):
        """
        Logger used by the simulator to store the relevant information.

        Parameters
        ----------
        save_path: 
            path to save file
        file_name:
            name of output hdf5 file
        """
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.file_path = self.save_path / "logger.hdf5"
        self.infection_location = []
        self.new_infected_ids = []
        # Remove if exists
        try:
            os.remove(self.file_path)
        except OSError:
            pass

    def log_population(
        self,
        population: Population,
        light_logger: bool = False,
        chunk_size: int = 100000,
    ):
        """
        Saves the Population object to hdf5 format file ``self.save_path``. Currently for each person,
        the following values are stored:
        - id, age, sex, super_area

        Parameters
        ----------
        population:
            population object
        chunk_size:
            number of people to save at a time. Note that they have to be copied to be saved,
            so keep the number below 1e6.
        """
        n_people = len(population.people)
        dt = h5py.vlen_dtype(np.dtype("int32"))
        # dt = tuple
        n_chunks = int(np.ceil(n_people / chunk_size))
        with h5py.File(self.file_path, "a", libver="latest") as f:
            people_dset = f.create_group("population")
            people_dset.attrs["n_people"] = n_people
            if not light_logger:
                for chunk in range(n_chunks):
                    idx1 = chunk * chunk_size
                    idx2 = min((chunk + 1) * chunk_size, n_people)
                    ids = []
                    ages = []
                    sexes = []
                    ethnicities = []
                    socioeconomic_indcs = []
                    super_areas = []

                    for person in population.people[idx1:idx2]:
                        ids.append(person.id)
                        ages.append(person.age)
                        ethnicities.append(person.ethnicity.encode("ascii", "ignore"))
                        socioeconomic_indcs.append(person.socioecon_index)
                        sexes.append(person.sex.encode("ascii", "ignore"))
                        super_areas.append(person.area.super_area.name)

                    ids = np.array(ids, dtype=np.int)
                    ages = np.array(ages, dtype=np.int16)
                    sexes = np.array(sexes, dtype="S10")
                    super_areas = np.array(super_areas, dtype="S10")
                    ethnicities = np.array(ethnicities, dtype="S10")
                    socioeconomic_indcs = np.array(socioeconomic_indcs, dtype=np.int8)

                    if chunk == 0:
                        people_dset.create_dataset(
                            "id", data=ids, maxshape=(None,), compression="gzip"
                        )
                        people_dset.create_dataset(
                            "age", data=ages, maxshape=(None,), compression="gzip"
                        )
                        people_dset.create_dataset(
                            "sex", data=sexes, maxshape=(None,), compression="gzip"
                        )
                        people_dset.create_dataset(
                            "ethnicity",
                            data=ethnicities,
                            maxshape=(None,),
                            compression="gzip",
                        )
                        people_dset.create_dataset(
                            "socioeconomic_index",
                            data=socioeconomic_indcs,
                            maxshape=(None,),
                            compression="gzip",
                        )
                        people_dset.create_dataset(
                            "super_area",
                            data=super_areas,
                            maxshape=(None,),
                            compression="gzip",
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
                        people_dset["ethnicity"].resize(newshape)
                        people_dset["ethnicity"][idx1:idx2] = ethnicities
                        people_dset["socioeconomic_index"].resize(newshape)
                        people_dset["socioeconomic_index"][
                            idx1:idx2
                        ] = socioeconomic_indcs

    def log_infected(
        self, date: "datetime", super_area_infections: dict,
    ):
        """
        Log relevant information of infected people per time step.

        Parameters
        ----------
        date:
            datetime of time step to log
        infected_ids:
            list of IDs of everyone infected 
        symptoms:
            list of symptoms of everyone infected
        n_secondary_infections:
            list of number of secondary infections for everyone infected
        """
        time_stamp = date.strftime("%Y-%m-%dT%H:%M:%S.%f")
        with h5py.File(self.file_path, "a", libver="latest") as f:
            for super_area in super_area_infections.keys():
                super_area_dset = f.require_group(super_area)
                super_area_dict = super_area_infections[super_area]
                infected_dset = super_area_dset.create_group(time_stamp)
                ids = np.array(super_area_dict["ids"], dtype=np.int64)
                symptoms = np.array(super_area_dict["symptoms"], dtype=np.int16)
                n_secondary_infections = np.array(
                    super_area_dict["n_secondary_infections"], dtype=np.int16
                )
                infected_dset.create_dataset("id", compression="gzip", data=ids)
                infected_dset.create_dataset(
                    "symptoms", compression="gzip", data=symptoms
                )
                infected_dset.create_dataset(
                    "n_secondary_infections",
                    compression="gzip",
                    data=n_secondary_infections,
                )

    def log_hospital_characteristics(self, hospitals: "Hospitals"):
        """
        Log hospital's coordinates and number of beds per hospital
        
        Parameters
        ----------
        hospitals:
            hospitals to log
        """
        coordinates = []
        n_beds = []
        n_icu_beds = []
        trust_code = []
        for hospital in hospitals:
            coordinates.append(hospital.coordinates)
            n_beds.append(hospital.n_beds)
            n_icu_beds.append(hospital.n_icu_beds)
            trust_code.append(hospital.trust_code)
        coordinates = np.array(coordinates, dtype=np.float16)
        n_beds = np.array(n_beds, dtype=np.int16)
        n_icu_beds = np.array(n_icu_beds, dtype=np.int16)
        trust_code = np.array(trust_code, dtype="S10")
        with h5py.File(self.file_path, "a", libver="latest") as f:
            hospital_dset = f.require_group("hospitals")
            hospital_dset.create_dataset("coordinates", data=coordinates)
            hospital_dset.create_dataset("n_beds", data=n_beds)
            hospital_dset.create_dataset("n_icu_beds", data=n_icu_beds)
            hospital_dset.create_dataset("trust_code", data=trust_code)

    def log_hospital_capacity(self, date: "datetime", hospitals: "Hospitals"):
        """
        Log the variation of number of patients in hospitals over time
    
        Parameters
        ----------
        date:
            date to log
        hospitals:
            hospitals to log
        """
        time_stamp = date.strftime("%Y-%m-%dT%H:%M:%S.%f")
        hospital_ids = []
        n_patients = []
        n_patients_icu = []
        for hospital in hospitals:
            hospital_ids.append(hospital.id)
            n_patients.append(
                len(hospital.subgroups[hospital.SubgroupType.patients].people)
            )
            n_patients_icu.append(
                len(hospital.subgroups[hospital.SubgroupType.icu_patients].people)
            )
        # save to hdf5
        hospitals_ids = np.array(hospital_ids, dtype=np.int16)
        n_patients = np.array(n_patients, dtype=np.int16)
        n_patients_icu = np.array(n_patients_icu, dtype=np.int16)
        with h5py.File(self.file_path, "a", libver="latest") as f:
            hospital_dset = f.require_group("hospitals")
            time_dset = hospital_dset.create_group(time_stamp)
            time_dset.create_dataset("hospital_id", data=hospital_ids)
            time_dset.create_dataset("n_patients", data=n_patients)
            time_dset.create_dataset("n_patients_icu", data=n_patients_icu)

    def get_number_group_instances(self, world: "World", location: str):
        """
        Given the world and a location, find the number of instances of that location that exist in the world

        Parameters
        ----------
        world:
            world instance
        location:
            location type
        """
        plural = location + "s"
        if location == "grocery":
            plural = "groceries"
        elif location == "company":
            plural = "companies"
        elif location == "commute_unit":
            plural = "commuteunits"
        elif location == "commutecity_unit":
            plural = "commutecityunits"
        return len(getattr(world, plural).members)

    def accumulate_infection_location(self, location, new_infected_ids):
        """
        Store where infections happend in a time step
        
        Parameters
        ----------
        location:
            group type of the group in which the infection took place
        """
        self.infection_location += [location] * len(new_infected_ids)
        self.new_infected_ids += new_infected_ids

    def log_infection_location(self, time):
        """
        Log where did all infections in a time step happened, as a number count

        Parameters
        ----------
        time:
            datetime to log
        """
        time_stamp = time.strftime("%Y-%m-%dT%H:%M:%S.%f")
        infection_location = np.array(self.infection_location, dtype="S")
        new_infected_ids = np.array(self.new_infected_ids, dtype=np.int)
        with h5py.File(self.file_path, "a", libver="latest") as f:
            locations_dset = f.require_group("locations")
            time_dset = locations_dset.create_group(time_stamp)
            time_dset.create_dataset("infection_location", data=infection_location)
            time_dset.create_dataset("new_infected_ids", data=new_infected_ids)
        self.infection_location = []
        self.new_infected_ids = []

    def unpack_dict(self, hdf5_obj, data, base_path, depth=0, max_depth=5):
        if depth > max_depth:
            return None
        for key, val in data.items():
            dset_path = f"{base_path}/{key}"
            if type(val) in [int, float, str, List[int], List[float], np.ndarray]:
                hdf5_obj.create_dataset(dset_path, data=val)
            elif isinstance(val, list):
                if all(isinstance(x, (int, float)) for x in val):
                    hdf5_obj.create_dataset(dset_path, data=val)
                elif all(isinstance(x, str) for x in val):
                    asciiList = [x.encode("ascii", "ignore") for x in val]
                    dt = h5py.string_dtype()
                    hdf5_obj.create_dataset(
                        dset_path, (len(asciiList),), dtype=dt, data=asciiList
                    )

            elif isinstance(val, datetime.datetime):
                hdf5_obj.create_dataset(
                    dset_path, data=val.strftime("%Y-%m-%dT%H:%M:%S.%f")
                )
            elif type(val) is dict:
                self.unpack_dict(
                    hdf5_obj, val, dset_path, depth=depth + 1
                )  # Recursion!!

    def log_parameters(
        self,
        interaction: "Interaction" = None,
        infection_seed: "InfectionSeed" = None,
        infection_selector: "InfectionSelector" = None,
        activity_manager: "ActivityManager" = None,
    ):
        with h5py.File(self.file_path, "a", libver="latest") as f:
            params = f.require_group("parameters")

            # interaction params
            if interaction is not None:
                for key, data in interaction.beta.items():
                    beta_path = f"parameters/beta/{key}"
                    f.create_dataset(beta_path, data=data)

                f.create_dataset(
                    "parameters/alpha_physical", data=interaction.alpha_physical
                )

                for key, data in interaction.contact_matrices.items():
                    dset_path = f"parameters/contact_matrices/{key}"
                    f.create_dataset(dset_path, data=data)

            if infection_selector is not None:
                f.create_dataset(
                    "parameters/asymptomatic_ratio",
                    data=infection_selector.health_index_generator.asymptomatic_ratio,
                )  #

            if infection_seed is not None:
                f.create_dataset(
                    "parameters/seed_strength", data=infection_seed.seed_strength
                )

            # policies
            if activity_manager is not None:
                if activity_manager.policies:
                    policy_types = defaultdict(int)
                    for pol in activity_manager.policies.policies:
                        policy_types[
                            pol.get_spec()
                        ] += 1  # How many of each type of policy?

                    for pol in activity_manager.policies.policies:
                        pol_spec = pol.get_spec()
                        n_instances = policy_types[pol_spec]

                        if n_instances > 1:
                            for i in range(1, n_instances + 1):
                                policy_path = f"parameters/policies/{pol_spec}/{i}"
                                # Loop through until we find a path that doesn't exist, then make it
                                if policy_path not in f:
                                    break
                        else:
                            i = None
                            policy_path = f"parameters/policies/{pol_spec}"

                        self.unpack_dict(f, pol.__dict__, policy_path, depth=0)
