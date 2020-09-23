import yaml
import logging
from enum import IntEnum
from june import paths
from typing import List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.groups import Group, Supergroup

from june.demography.geography import SuperArea
from june.infection import SymptomTag

logger = logging.getLogger(__name__)

default_data_filename = (
    paths.data_path / "input/hospitals/trusts.csv"
)
default_config_filename = paths.configs_path / "defaults/groups/hospitals.yaml"


class Hospital(Group):
    """
    The Hospital class represents a hospital and contains information about
    its patients and workers - the latter being the usual "people".

    We currently use three subgroups: 
    0 - workers (i.e. nurses, doctors, etc.),
    1 - patients
    2 - ICU patients
    """

    class SubgroupType(IntEnum):
        workers = 0
        patients = 1
        icu_patients = 2

    __slots__ = "id", "n_beds", "n_icu_beds", "coordinates", "area", "trust_code" 

    def __init__(
        self,
        n_beds: int,
        n_icu_beds: int,
        area: str = None,
        coordinates: Optional[Tuple[float, float]] = None,
        trust_code: str = None,
    ):
        """
        Create a Hospital given its description.

        Parameters
        ----------
        n_beds:
            total number of regular beds in the hospital
        n_icu_beds:
            total number of ICU beds in the hospital
        area:
            name of the super area the hospital belongs to
        coordinates:
            latitude and longitude 
        """
        super().__init__()
        self.area = area 
        self.coordinates = coordinates
        self.n_beds = n_beds
        self.n_icu_beds = n_icu_beds
        self.trust_code = trust_code

    @property
    def super_area(self):
        return self.area.super_area

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
                person, activity="medical_facility", subgroup_type=subgroup_type,
            )
        else:
            super().add(
                person,
                activity="primary_activity",
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

        if person.infection.tag == SymptomTag.intensive_care:
            self.add(person, self.SubgroupType.icu_patients)
        elif person.infection.tag == SymptomTag.hospitalised:
            self.add(person, self.SubgroupType.patients)
        else:
            raise AssertionError(
                "ERROR: This person shouldn't be trying to get to a hospital"
            )

    def release_as_patient(self, person):
        person.subgroups.medical_facility = None

class Hospitals(Supergroup):
    def __init__(
        self,
        hospitals: List["Hospital"],
        neighbour_hospitals: int = 5, 
        box_mode: bool = False,
    ):
        """
        Create a group of hospitals, and provide functionality to locate patients
        to a nearby hospital. It will check in order the first ```neighbour_hospitals```,
        when one has space available the patient is allocated to it. If none of the closest
        ones has beds available it will pick one of them at random and that hospital will
        overflow

        Parameters
        ----------
        hospitals:
            list of hospitals to aggrupate
        neighbour_hospitals:
            number of closest hospitals to look for
        box_mode:
            whether to run in single box mode, or full simulation
        """
        super().__init__()
        self.box_mode = box_mode
        self.members = hospitals
        self.neighbour_hospitals = neighbour_hospitals
        coordinates = np.array([hospital.coordinates for hospital in hospitals])
        if not box_mode:
            self.init_trees(coordinates)

    @classmethod
    def for_box_mode(cls):
        hospitals = []
        hospitals.append(Hospital(coordinates=None, n_beds=10, n_icu_beds=2,))
        hospitals.append(Hospital(coordinates=None, n_beds=5000, n_icu_beds=5000,))
        return cls(hospitals, neighbour_hospitals=None, box_mode=True)

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
        neighbour_hospitals = config["neighbour_hospitals"]
        logger.info(f"There are {len(hospital_df)} hospitals in the world.")
        hospitals = cls.init_hospitals(cls, hospital_df)
        return Hospitals(hospitals, neighbour_hospitals)

    @classmethod
    def for_geography(
        cls,
        geography,
        filename: str = default_data_filename,
        config_filename: str = default_config_filename,
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        neighbour_hospitals = config["neighbour_hospitals"]
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
                        super_area, hospitals_in_area, 
                    )
                    hospitals.append(hospital)
                else:
                    for _, row in hospitals_in_area.iterrows():
                        hospital = cls.create_hospital_from_df_row(
                            super_area, row,  
                        )
                        hospitals.append(hospital)
                if len(hospitals) == total_hospitals:
                    break
        return cls(hospitals, neighbour_hospitals, False)

    @classmethod
    def create_hospital_from_df_row(
        cls, super_area, row,  
    ):
        coordinates = row[["latitude", "longitude"]].values.astype(np.float)
        n_beds = row["beds"]
        n_icu_beds = row["icu_beds"] 
        trust_code = row["code"]
        hospital = Hospital(
            super_area=super_area,
            coordinates=coordinates,
            n_beds=n_beds,
            n_icu_beds=n_icu_beds,
            trust_code=trust_code,
        )
        return hospital

    def init_hospitals(
        self, hospital_df: pd.DataFrame, 
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
            n_icu_beds = row["icu_beds"] 
            trust_code = row["code"]
            coordinates = row[["latitude", "longitude"]].values.astype(np.float)
            hospital = Hospital(
                coordinates=coordinates,
                n_beds=n_beds,
                n_icu_beds=n_icu_beds,
                trust_code=trust_code,
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
        assign_icu = person.infection.tag == SymptomTag.intensive_care
        assign_patient = person.infection.tag == SymptomTag.hospitalised

        if self.box_mode:
            for hospital in self.members:
                if assign_patient and not hospital.full:
                    return hospital
                if assign_icu and not hospital.full_ICU:
                    return hospital
        else:
            hospital = None
            hospitals_idx = self.get_closest_hospitals(
                coordinates=person.area.coordinates, k=self.neighbour_hospitals
            )
            closest_hospitals = []
            for hospital_id in hospitals_idx:
                hospital = self.members[hospital_id]
                closest_hospitals.append(hospital)
                if (assign_patient and not hospital.full) or (
                    assign_icu and not hospital.full_ICU
                ):
                    break 
            if hospital is None:
                random_number = np.random.randint(
                        0, min(len(closest_hospitals), len(self.members))
                        )
                hospital = closest_hospitals[random_number]
            hospital.add_as_patient(person)

    def get_closest_hospitals(
        self, coordinates: Tuple[float, float], k: int 
    ) -> Tuple[float, float]:
        """
        Get the k-th closest hospital to a given coordinate

        Parameters
        ---------
        coordinates: 
            latitude and longitude
        k:
            k-th neighbour

        Returns
        -------
        ID of the k-th closest hospital

        """
        k = min(k, len(list(self.hospital_trees.data)))
        distances, neighbours = self.hospital_trees.query(
            np.deg2rad(coordinates.reshape(1, -1)),
            k = k,
            sort_results=True,
        )
        return neighbours[0]
