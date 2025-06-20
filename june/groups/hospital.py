import yaml
import logging
import random
from enum import IntEnum
from june import paths
from typing import List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from june.global_context import GlobalContext
from june.groups import Group, Supergroup, ExternalGroup, ExternalSubgroup
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
        """
        Initialize the hospital with a disease configuration.

        Parameters
        ----------
        disease_config : DiseaseConfig
            Configuration object for the disease.
        """
        self.ward_ids = set()  # IDs of patients in the ward
        self.icu_ids = set()   # IDs of patients in the ICU

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

        To correctly log if the person has been just admitted, transferred, or released,
        we return a few flags:
        - "ward_admitted": This person has been admitted to the ward.
        - "icu_admitted": This person has been directly admitted to ICU.
        - "ward_transferred": This person has been transferred to ward (from ICU).
        - "icu_transferred": This person has been transferred to ICU (from ward).
        - "no_change": No change respect to last time step.
        """
        disease_config = GlobalContext.get_disease_config()
        # Get the person's current symptom tag
        person_tag = person.infection.tag

        # Ensure person_tag is resolved to a value (integer) if it's an object
        person_tag_value = person_tag.value if hasattr(person_tag, "value") else person_tag

        # Check if the person is entering a hospital
        if (
            person.medical_facility is None
            or person.medical_facility.spec != "hospital"
        ):
            if person_tag_value == disease_config.symptom_manager.get_tag_value("hospitalised"):
                self.add_to_ward(person)
                return "ward_admitted"
            elif person_tag_value == disease_config.symptom_manager.get_tag_value("intensive_care"):
                self.add_to_icu(person)
                return "icu_admitted"
            else:
                raise HospitalError(
                    f"Person with symptoms {person_tag} (value: {person_tag_value}) "
                )
        else:
            # The person is already in a hospital
            if person_tag_value == disease_config.symptom_manager.get_tag_value("hospitalised"):
                if person.id in self.ward_ids:
                    return "no_change"
                else:
                    self.remove_from_icu(person)
                    self.add_to_ward(person)
                    return "ward_transferred"
            elif person_tag_value == disease_config.symptom_manager.get_tag_value("intensive_care"):
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
            raise HospitalError("Trying to release patient not located in icu or ward.")


class Hospital(Group, AbstractHospital, MedicalFacility):
    """
    The Hospital class represents a hospital and contains information about
    its patients and workers - the latter being the usual "people".

    We currently use three subgroups:
    0 - workers (i.e. nurses, doctors, etc.),
    1 - patients
    2 - ICU patients
    """

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
        n_beds: int
            Total number of regular beds in the hospital.
        n_icu_beds: int
            Total number of ICU beds in the hospital.
        disease_config: DiseaseConfig
            Configuration object for the disease.
        area: str, optional
            Name of the super area the hospital belongs to.
        coordinates: tuple of float, optional
            Latitude and longitude.
        trust_code: str, optional
            Trust code associated with the hospital.
        """
        # Initialize the base Group class with disease_config
        Group.__init__(self)

        # Initialize AbstractHospital with disease_config
        AbstractHospital.__init__(self)

        # Assign attributes specific to Hospital
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

    def add(self, person, subgroup_type):
        if subgroup_type in [
            self.SubgroupType.patients,
            self.SubgroupType.icu_patients,
        ]:
            super().add(
                person, activity="medical_facility", subgroup_type=subgroup_type
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
    venue_class = Hospital

    def __init__(
        self, hospitals: List["Hospital"], neighbour_hospitals: int = 5, ball_tree=True
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
        """
        Create hospitals for the given geography based on input files and disease configuration.

        Parameters
        ----------
        geography : Geography
            The geography object containing areas.
        filename : str
            Path to the file containing hospital data.
        config_filename : str
            Path to the configuration file.
        disease_config : DiseaseConfig, optional
            The disease configuration object to use for initializing hospitals.

        Returns
        -------
        cls
            An instance of the Hospitals class.
        """
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
                        area, hospitals_in_area
                    )
                    hospitals.append(hospital)
                else:
                    for _, row in hospitals_in_area.iterrows():
                        hospital = cls.create_hospital_from_df_row(
                            area, row
                        )
                        hospitals.append(hospital)
                if len(hospitals) == total_hospitals:
                    break

        # Debugging: View hospital data as a DataFrame
        hospitals_data = [{
            "| Hospital ID": hospital.id,
            "| Area": hospital.area.name,
            "| Coordinates": hospital.coordinates,
            "| Total Beds": hospital.n_beds,
            "| ICU Beds": hospital.n_icu_beds,
            "| Trust Code": hospital.trust_code
        } for hospital in hospitals]

        hospitals_df = pd.DataFrame(hospitals_data)
        print("\n===== Sample of Created Hospitals =====")
        print(hospitals_df.head())

        return cls(
            hospitals=hospitals, neighbour_hospitals=neighbour_hospitals, ball_tree=True
        )

    @classmethod
    def create_hospital_from_df_row(cls, area, row):
        """
        Create a hospital from a row in the hospital dataframe.

        Parameters
        ----------
        area : Area
            The area object associated with the hospital.
        row : pd.Series
            The row from the hospital dataframe.
        disease_config : DiseaseConfig
            The disease configuration object.

        Returns
        -------
        Hospital
            A newly created Hospital instance.
        """
        coordinates = row[["latitude", "longitude"]].values.astype(np.float64)
        n_beds = row["beds"]
        n_icu_beds = row["icu_beds"]
        trust_code = row["code"]

        # Pass DiseaseConfig to the hospital initialization
        hospital = cls.venue_class(
            area=area,
            coordinates=coordinates,
            n_beds=n_beds,
            n_icu_beds=n_icu_beds,
            trust_code=trust_code
        )
        return hospital

    def init_hospitals(self, hospital_df: pd.DataFrame) -> List["Hospital"]:
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
            np.deg2rad(hospital_coordinates), metric="haversine"
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
            np.deg2rad(coordinates.reshape(1, -1)), k=k, sort_results=True
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
            np.deg2rad(coordinates.reshape(1, -1)), k=k, sort_results=True
        )
        return [self.members[index] for index in neighbours[0]]


class ExternalHospital(ExternalGroup, AbstractHospital, MedicalFacility):
    external = True
    __slots__ = "spec", "id", "domain_id", "region_name", "ward_ids", "icu_ids"

    class SubgroupType(IntEnum):
        workers = 0
        patients = 1
        icu_patients = 2

    def __init__(self, id, spec, domain_id, region_name):
        ExternalGroup.__init__(self, id=id, spec=spec, domain_id=domain_id)
        AbstractHospital.__init__(self)
        self.region_name = region_name

        self.ward = ExternalSubgroup(
            group=self, subgroup_type=self.SubgroupType.patients
        )
        self.icu = ExternalSubgroup(
            group=self, subgroup_type=self.SubgroupType.icu_patients
        )
