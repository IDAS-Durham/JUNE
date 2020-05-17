import os
import yaml
import logging
import os
import h5py
from enum import IntEnum
from june import paths
from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.groups import Group, Supergroup

from june.geography import SuperArea

logger = logging.getLogger(__name__)
nan_integer = -999

default_data_filename = (
    paths.data_path / "processed/hospital_data/england_hospitals.csv"
)
default_config_filename = paths.configs_path / "defaults/groups/hospitals.yaml"


class Hospital(Group):
    """
    The Hospital class represents a hospital and contains information about
    its patients and workers - the latter being the usual "people".

    TODO: we have to figure out the inheritance structure; I think it will
    be an admixture of household and company.
    I will also assume that the patients cannot infect anybody - this may
    become a real problem as it is manifestly not correct.

    We currently use three subgroups: 
    0 - workers (i.e. nurses, doctors, etc.),
    1 - patients
    2 - ICU patients
    """

    class SubgroupType(IntEnum):
        workers = 0
        patients = 1
        icu_patients = 2

    __slots__ = "id", "n_beds", "n_icu_beds", "coordinates", "super_area"

    def __init__(
        self,
        n_beds: int,
        n_icu_beds: int,
        super_area: str = None,
        coordinates: tuple = None,  # Optional[Tuple[float, float]] = None,
    ):
        """
        Create a Hospital given its description.

        Parameters
        ----------
        n_beds:
            total number of regular beds in the hospital
        n_icu_beds:
            total number of ICU beds in the hospital
        coordinates:
            latitude and longitude 
        msoa_name:
            name of the msoa area the hospital belongs to
        """
        super().__init__()
        self.super_area = super_area
        self.coordinates = coordinates
        self.n_beds = n_beds
        self.n_icu_beds = n_icu_beds

    @property
    def full(self):
        """
        Check whether all regular beds are being used
        """
        return self[self.SubgroupType.patients].size >= self.n_beds

    @property
    def full_ICU(self):
        """
        Check whether all ICU beds are being used
        """
        return self[self.SubgroupType.icu_patients].size >= self.n_icu_beds

    def add(self, person, subgroup_type=SubgroupType.workers):
        if subgroup_type in [
            self.SubgroupType.patients,
            self.SubgroupType.icu_patients,
        ]:
            super().add(
                person,
                activity_type=person.ActivityType.hospital,
                subgroup_type=subgroup_type,
            )
        else:
            super().add(
                person,
                activity_type=person.ActivityType.primary_activity,
                subgroup_type=self.SubgroupType.workers,
            )

    @property
    def icu_patients(self):
        return self.subgroups[self.SubgroupType.icu_patients]

    @property
    def patients(self):
        return self.subgroups[self.SubgroupType.patients]

    def add_as_patient(self, person):
        """
        Add patient to hospital, depending on their healty information tag
        they'll go to intensive care or regular beds.

        Parameters
        ----------
        person:
            person instance to add as patient
        """
        if person.health_information.tag == "intensive care":
            self.add(person, self.SubgroupType.icu_patients)
        elif person.health_information.tag == "hospitalised":
            self.add(person, self.SubgroupType.patients)
        else:
            raise AssertionError(
                "ERROR: This person shouldn't be trying to get to a hospital"
            )

    def release_as_patient(self, person):
        person.subgroups[person.ActivityType.hospital] = None

    def move_patient_within_hospital(self, person):
        if person.health_information.tag == "intensive care":
            person.subgroups[person.ActivityType.hospital] = person.hospital.group[
                self.SubgroupType.icu_patients
            ]
        elif person.health_information.tag == "hospitalised":
            person.subgroups[person.ActivityType.hospital] = person.hospital.group[
                self.SubgroupType.patients
            ]
        else:
            raise AssertionError(
                "ERROR: This person shouldn't be trying to get to a hospital"
            )


class Hospitals(Supergroup):
    def __init__(
        self,
        hospitals: List["Hospital"],
        max_distance: float = 100,
        box_mode: bool = False,
    ):
        """
        Create a group of hospitals, and provide functionality to locate patients
        to a nearby hospital.

        Parameters
        ----------
        box_mode:
            whether to run in single box mode, or full simulation
        """
        super().__init__()
        self.box_mode = box_mode
        self.max_distance = max_distance
        self.members = hospitals
        coordinates = np.array([hospital.coordinates for hospital in hospitals])
        if not box_mode:
            self.init_trees(coordinates)

    @classmethod
    def for_box_mode(cls):
        hospitals = []
        hospitals.append(Hospital(coordinates=None, n_beds=10, n_icu_beds=2,))
        hospitals.append(Hospital(coordinates=None, n_beds=5000, n_icu_beds=5000,))
        return cls(hospitals, box_mode=True)

    @classmethod
    def from_file(
        cls,
        filename: str = default_data_filename,
        config_filename: str = default_config_filename,
    ) -> "Hospitals":
        """
        Initialize Hospitals from path to data frame, and path to config file.

        Parameters
        ----------
        filename:
            path to hospital dataframe
        config_filename:
            path to hospital config dictionary

        Returns
        -------
        Hospitals instance
        """

        hospital_df = pd.read_csv(filename)
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        max_distance = config["max_distance"]
        icu_fraction = config["icu_fraction"]
        logger.info(f"There are {len(hospital_df)} hospitals in the world.")
        hospitals = cls.init_hospitals(cls, hospital_df, icu_fraction)
        return Hospitals(hospitals, max_distance)

    @classmethod
    def for_geography(
        cls,
        geography,
        filename: str = default_data_filename,
        config_filename: str = default_config_filename,
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)

        max_distance = config["max_distance"]
        icu_fraction = config["icu_fraction"]
        hospital_df = pd.read_csv(filename, index_col=0)
        super_area_names = [super_area.name for super_area in geography.super_areas]
        hospital_df = hospital_df.loc[hospital_df.index.isin(super_area_names)]
        logger.info(f"There are {len(hospital_df)} hospitals in this geography.")
        total_hospitals = len(hospital_df)
        hospitals = []
        for super_area in geography.super_areas:
            if super_area.name in hospital_df.index:
                hospitals_in_area = hospital_df.loc[super_area.name]
                if isinstance(hospitals_in_area, pd.Series):
                    hospital = cls.create_hospital_from_df_row(
                        super_area, hospitals_in_area, icu_fraction
                    )
                    hospitals.append(hospital)
                else:
                    for _, row in hospitals_in_area.iterrows():
                        hospital = cls.create_hospital_from_df_row(
                            super_area, row, icu_fraction
                        )
                        hospitals.append(hospital)
                if len(hospitals) == total_hospitals:
                    break
        return cls(hospitals, max_distance, False)

    @classmethod
    def create_hospital_from_df_row(cls, super_area, row, icu_fraction):
        coordinates = row[["Latitude", "Longitude"]].values.astype(np.float)
        n_beds = row["beds"]
        n_icu_beds = round(icu_fraction * n_beds)
        n_beds -= n_icu_beds
        hospital = Hospital(
            super_area=super_area,
            coordinates=coordinates,
            n_beds=n_beds,
            n_icu_beds=n_icu_beds,
        )
        return hospital

    def init_hospitals(
        self, hospital_df: pd.DataFrame, icu_fraction: float
    ) -> List["Hospital"]:
        """
        Create Hospital objects with the right characteristics,
        as given by dataframe.

        Parameters
        ----------
        hospital_df:
            dataframe with hospital characteristics data
        """
        hospitals = []
        for index, row in hospital_df.iterrows():
            n_beds = row["beds"]
            n_icu_beds = round(icu_fraction * n_beds)
            n_beds -= n_icu_beds
            # msoa_name = row["MSOA"]
            coordinates = row[["Latitude", "Longitude"]].values.astype(np.float)
            # create hospital
            hospital = Hospital(
                # super_area=,
                coordinates=coordinates,
                n_beds=n_beds,
                n_icu_beds=n_icu_beds,
            )
            hospitals.append(hospital)
        return hospitals

    def init_trees(self, hospital_coordinates: np.array) -> BallTree:
        """
        Reads hospital location and sizes, it initializes a KD tree on a sphere,
        to query the closest hospital to a given location.

        Parameters
        ----------
        hospital_df: 
            dataframe with hospital characteristics data

        Returns
        -------
        Tree to query nearby schools
        """
        self.hospital_trees = BallTree(
            np.deg2rad(hospital_coordinates), metric="haversine",
        )

    def allocate_patient(self, person: "Person"):
        """
        Function to allocate patients into close by hospitals with available beds.
        If there are no available beds within a maximum distance, the patient is
        not allocated.

        Parameters
        ----------
        person: 
            patient to allocate into a hospital 
        Returns
        -------
        hospital with availability

        """
        assign_icu = person.health_information.tag == "intensive care"
        assign_patient = person.health_information.tag == "hospitalised"

        if self.box_mode:
            for hospital in self.members:
                if assign_patient and not hospital.full:
                    return hospital
                if assign_icu and not hospital.full_ICU:
                    return hospital
        else:
            hospital = None
            # find hospitals  within radius of max distance
            distances, hospitals_idx = self.get_closest_hospitals(
                person.area.coordinates, self.max_distance
            )
            for distance, hospital_id in zip(distances, hospitals_idx):
                hospital = self.members[hospital_id]
                if distance > self.max_distance:
                    break
                if (assign_icu and not hospital.full) or (
                    assign_patient and not hospital.full_ICU
                ):
                    break
            if hospital is not None:

                logger.debug(
                    f"Receiving hospital for patient with "
                    + f"{person.health_information.tag} at distance = {distance} km"
                )
                hospital.add_as_patient(person)
            else:
                logger.info(
                    f"no hospital found for patient with "
                    + f"{person.health_information.tag} in distance "
                    + f"< {self.max_distance} km."
                )

    def get_closest_hospitals(
        self, coordinates: Tuple[float, float], r_max: float
    ) -> Tuple[float, float]:
        """
        Get the closest hospitals to a given coordinate within r_max

        Parameters
        ----------
        coordinates: 
            latitude and longitude
        r_max:
            maximum distance to hospital

        Returns
        -------
        Distance to the closest hospitals, in km 
        ID of the hospitals within r_max, ordered by distance

        """
        earth_radius = 6371.0  # km
        r_max /= earth_radius
        idx, distances = self.hospital_trees.query_radius(
            np.deg2rad(coordinates.reshape(1, -1)),
            r=r_max,
            return_distance=True,
            sort_results=True,
        )
        distances = np.array(distances[0]) * earth_radius
        return distances, idx[0]

    def to_hdf5(self, file_path: str):
        n_hospitals = len(self.members)
        ids = []
        n_beds = []
        n_icu_beds = []
        super_areas = []
        coordinates = []
        for hospital in self.members:
            ids.append(hospital.id)
            if hospital.super_area is None:
                super_areas.append(nan_integer)
            else:
                super_areas.append(hospital.super_area.id)
            n_beds.append(hospital.n_beds)
            n_icu_beds.append(hospital.n_icu_beds)
            coordinates.append(np.array(hospital.coordinates))

        ids = np.array(ids, dtype=np.int)
        super_areas = np.array(super_areas, dtype=np.int)
        n_beds = np.array(n_beds, dtype=np.int)
        n_icu_beds = np.array(n_icu_beds, dtype=np.int)
        coordinates = np.array(coordinates, dtype=np.float)
        with h5py.File(file_path, "w") as f:
            people_dset = f.create_group("hospitals")
            people_dset.attrs["n_hospitals"] = n_hospitals
            people_dset.create_dataset("id", data=ids)
            people_dset.create_dataset("super_area", data=super_areas)
            people_dset.create_dataset("n_beds", data=n_beds)
            people_dset.create_dataset("n_icu_beds", data=n_icu_beds)
            people_dset.create_dataset("coordinates", data=coordinates)

    @classmethod
    def from_hdf5(cls, file_path: str):
        with h5py.File(file_path, "r") as f:
            hospitals = f["hospitals"]
            hospitals_list = list()
            chunk_size = 50000
            n_hospitals = hospitals.attrs["n_hospitals"]
            n_chunks = int(np.ceil(n_hospitals / chunk_size))
            for chunk in range(n_chunks):
                idx1 = chunk * chunk_size
                idx2 = min((chunk + 1) * chunk_size, n_hospitals)
                ids = hospitals["id"]
                super_areas = hospitals["super_area"][idx1:idx2]
                n_beds_list = hospitals["n_beds"][idx1:idx2]
                n_icu_beds_list = hospitals["n_icu_beds"][idx1:idx2]
                coordinates = hospitals["coordinates"][idx1:idx2]
                for k in range(idx2 - idx1):
                    super_area = super_areas[k]
                    if super_area == nan_integer:
                        super_area = None
                    hospital = Hospital(
                        n_beds_list[k], n_icu_beds_list[k], super_area, coordinates[k]
                    )
                    hospital.id = ids[k]
                    hospitals_list.append(hospital)
        return cls(hospitals_list)
