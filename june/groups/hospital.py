import yaml
import logging
from enum import IntEnum
from june import paths
from typing import List, Tuple, Optional
from random import random
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.groups import Group, Supergroup, ExternalGroup, ExternalSubgroup
from june.geography import SuperArea
from june.epidemiology.infection import SymptomTag
from june.exc import HospitalError

logger = logging.getLogger("hospitals")

default_data_filename = paths.data_path / "input/hospitals/trusts.csv"
default_config_filename = paths.configs_path / "defaults/groups/hospitals.yaml"


class MedicalFacility:
    pass


class MedicalFacilities:
    pass


class AbstractHospital:
    """
    Hospital functionality common for all hospitals (internal to the domain and external).
    """

    def __init__(self):
        self.ward_ids = set()
        self.icu_ids = set()

    def add_to_ward(self, person):
        self.ward_ids.add(person.id)
        person.subgroups.medical_facility = self.ward

    def remove_from_ward(self, person):
        self.ward_ids.remove(person.id)
        person.subgroups.medical_facility = None

    def add_to_icu(self, person):
        self.icu_ids.add(person.id)
        person.subgroups.medical_facility = self.icu

    def remove_from_icu(self, person):
        self.icu_ids.remove(person.id)
        person.subgroups.medical_facility = None

    def allocate_patient(self, person):
        """
        Allocate a patient inside the hospital, in the ward, in the ICU, or transfer.
        To correctly log if the person has been just admitted, transfered, or released,
        we return a few flags:
        - "ward_admitted" : this person has been admitted to the ward.
        - "icu_admitted" : this person has been directly admitted to icu.
        - "ward_transferred" : this person has been transferred  to ward (from icu)
        - "icu_transferred" : this person has been transferred to icu (from ward)
        - "no_change" : no change respect to last time step.
        """
        if (
            person.medical_facility is None
            or person.medical_facility.spec != "hospital"
        ):
            if person.infection.tag.name == "hospitalised":
                self.add_to_ward(person)
                return "ward_admitted"
            elif person.infection.tag.name == "intensive_care":
                self.add_to_icu(person)
                return "icu_admitted"
            else:
                raise HospitalError(
                    f"Person with symptoms {person.infection.tag} trying to enter hospital."
                )
        else:
            # this person has already been allocated in a hospital (this one)
            if person.infection.tag.name == "hospitalised":
                if person.id in self.ward_ids:
                    return "no_change"
                else:
                    self.remove_from_icu(person)
                    self.add_to_ward(person)
                    return "ward_transferred"
            elif person.infection.tag.name == "intensive_care":
                if person.id in self.icu_ids:
                    return "no_change"
                else:
                    self.remove_from_ward(person)
                    self.add_to_icu(person)
                    return "icu_transferred"

    def release_patient(self, person):
        """
        Releases patient from hospital.
        """
        if person.id in self.ward_ids:
            self.remove_from_ward(person)
        elif person.id in self.icu_ids:
            self.remove_from_icu(person)
        else:
            raise HospitalError(
                f"Trying to release patient not located in icu or ward."
            )


class Hospital(Group, AbstractHospital, MedicalFacility):
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
        Group.__init__(self)
        AbstractHospital.__init__(self)
        self.area = area
        self.coordinates = coordinates
        self.n_beds = n_beds
        self.n_icu_beds = n_icu_beds
        self.trust_code = trust_code

    @property
    def super_area(self):
        return self.area.super_area

    @property
    def region(self):
        return self.super_area.region

    @property
    def region_name(self):
        return self.region.name

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
                activity="medical_facility",
                subgroup_type=subgroup_type,
            )
        else:
            super().add(
                person,
                activity="primary_activity",
                subgroup_type=self.SubgroupType.workers,
            )

    @property
    def ward(self):
        return self.subgroups[self.SubgroupType.patients]

    @property
    def icu(self):
        return self.subgroups[self.SubgroupType.icu_patients]


class Hospitals(Supergroup, MedicalFacilities):
    def __init__(
        self,
        hospitals: List["Hospital"],
        neighbour_hospitals: int = 5,
        ball_tree=True,
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
        """
        super().__init__(members=hospitals)
        self.neighbour_hospitals = neighbour_hospitals
        if ball_tree and self.members:
            coordinates = np.array([hospital.coordinates for hospital in hospitals])
            self.init_trees(coordinates)

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
        hospital_df = pd.read_csv(filename, index_col=4)
        area_names = [area.name for area in geography.areas]
        hospital_df = hospital_df.loc[hospital_df.index.isin(area_names)]
        logger.info(f"There are {len(hospital_df)} hospitals in this geography.")
        total_hospitals = len(hospital_df)
        hospitals = []
        for area in geography.areas:
            if area.name in hospital_df.index:
                hospitals_in_area = hospital_df.loc[area.name]
                if isinstance(hospitals_in_area, pd.Series):
                    hospital = cls.create_hospital_from_df_row(
                        area,
                        hospitals_in_area,
                    )
                    hospitals.append(hospital)
                else:
                    for _, row in hospitals_in_area.iterrows():
                        hospital = cls.create_hospital_from_df_row(
                            area,
                            row,
                        )
                        hospitals.append(hospital)
                if len(hospitals) == total_hospitals:
                    break
        return cls(
            hospitals=hospitals, neighbour_hospitals=neighbour_hospitals, ball_tree=True
        )

    @classmethod
    def create_hospital_from_df_row(
        cls,
        area,
        row,
    ):
        coordinates = row[["latitude", "longitude"]].values.astype(np.float64)
        n_beds = row["beds"]
        n_icu_beds = row["icu_beds"]
        trust_code = row["code"]
        hospital = Hospital(
            area=area,
            coordinates=coordinates,
            n_beds=n_beds,
            n_icu_beds=n_icu_beds,
            trust_code=trust_code,
        )
        return hospital

    def init_hospitals(
        self,
        hospital_df: pd.DataFrame,
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
            coordinates = row[["latitude", "longitude"]].values.astype(np.float64)
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
            np.deg2rad(hospital_coordinates),
            metric="haversine",
        )

    def get_closest_hospitals_idx(
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
            k=k,
            sort_results=True,
        )
        return neighbours[0]

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
            k=k,
            sort_results=True,
        )
        return [self.members[index] for index in neighbours[0]]


class ExternalHospital(ExternalGroup, AbstractHospital):
    external = True
    __slots__ = "spec", "id", "domain_id", "region_name", "ward_ids", "icu_ids"

    def __init__(self, id, spec, domain_id, region_name):
        ExternalGroup.__init__(self, id=id, spec=spec, domain_id=domain_id)
        AbstractHospital.__init__(self)
        self.region_name = region_name
        self.ward = ExternalSubgroup(
            group=self, subgroup_type=Hospital.SubgroupType.patients
        )
        self.icu = ExternalSubgroup(
            group=self, subgroup_type=Hospital.SubgroupType.icu_patients
        )
