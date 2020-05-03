import logging
import numpy as np
import pandas as pd
import yaml
from sklearn.neighbors._ball_tree import BallTree
from covid.groups import Group
from typing import List, Tuple, Dict


ic_logger = logging.getLogger(__name__)


class Hospital(Group):
    """
    The Hospital class represents a hospital and contains information about 
    its patients and workers - the latter being the usual "people".

    TODO: we have to figure out the inheritance structure; I think it will
    be an admixture of household and company.
    I will also assume that the patients cannot infect anybody - this may
    become a real problem as it is manifestly not correct.
    """

    def __init__(self, hospital_id: int, n_beds: int, n_icu_beds: int, coordinates: Tuple[float, float], msoa_name: str=None):
        """
        Create a Hospital given its description.

        Parameters
        ----------
        hospital_id:
            unique identifier of the hospital 
        n_beds:
            total number of regular beds in the hospital
        n_icu_beds:
            total number of ICU beds in the hospital
        coordinates:
            latitude and longitude 
        msoa_name:
            name of the msoa area the hospital belongs to

        """

        super().__init__("Hospital_%03d" % hospital_id, "hospital")
        self.id = hospital_id
        self.n_beds = n_beds
        self.n_icu_beds = n_icu_beds
        self.coordinates = coordinates
        self.msoa_name = msoa_name
        self.n_medics = 0
        self.people = []
        self.nurses = []
        self.doctors = []
        self.patients = []
        self.icu_patients = []

    @property
    def full(self):
        """
        Check whether all regular beds are being used
        """
        return len(self.patients) >= self.n_beds

    @property
    def full_ICU(self):
        """
        Check whether all ICU beds are being used
        """
        return len(self.icu_patients) >= self.n_icu_beds

    def set_active_members(self):
        """
        Set people in hospital active in hospital only
        """
        for person in self.people:
            if person.active_group is None:
                person.active_group = "hospital"

    def add_as_patient(self, person: "Person"):
        """
        Add patient to hospital, depending on their healty information tag
        they'll go to intensive care or regular beds.

        Parameters
        ----------
        person: 
            person instance to add as patient
        """
        if person.health_information.tag == "intensive care":
            self.icu_patients.append(person)
            person.in_hospital = self
        elif person.health_information.tag == "hospitalised":
            self.patients.append(person)
            person.in_hospital = self
        else:
            ic_logger.info("ERROR: This person shouldnt be trying to get to a hospital")
            pass

    def release_as_patient(self, person):
        """
        Release a patient from hospital

        Parameters
        ----------
        person: 
            person instance to remove as patient
        """
        if person in self.patients:
            self.patients.remove(person)
        elif person in self.icu_patients:
            self.icu_patients.remove(person)
        person.in_hospital = None

    @property
    def size(self):
        return len(self.people) + len(self.patients) + len(self.icu_patients)

    def update_status_lists_for_patients(self):
        """
        Update the health information of patients, and move them around if necessary
        """
        dead = []
        for person in self.patients:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                ic_logger.info(
                    "ERROR: in our current setup, only infected patients in the hospital"
                )
                self.susceptible.append(person)
            if person.health_information.infected:
                if not (person.health_information.in_hospital):
                    # TODO: is this necessary? How could they have made it to hospital?
                    ic_logger.info("ERROR: wrong tag for infected patient in hospital")
                    self.patients.remove(person)
                if person.health_information.tag == "intensive care":
                    self.icu_patients.append(person)
                    self.patients.remove(person)
            if person.health_information.recovered:
                self.release_as_patient(person)
            if person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.patients.remove(person)

    def update_status_lists_for_ICUpatients(self):
        """
        Update the health information of ICU patients, and move them around if necessary
        """

        dead = []
        for person in self.icu_patients:
            person.health_information.update_health_status()
            if person.health_information.susceptible:
                ic_logger.info(
                    "ERROR: in our current setup, only infected patients in the hospital"
                )
                self.susceptible.append(person)
            if person.health_information.infected:
                if not (person.health_information.in_hospital):
                    ic_logger.info("ERROR: wrong tag for infected patient in hospital")
                    self.icu_patients.remove(person)
                if person.health_information.tag == "hospitalised":
                    self.patients.append(person)
                    self.icu_patients.remove(person)
            if person.health_information.recovered:
                self.release_as_patient(person)
            if person.health_information.dead:
                person.bury()
                dead.append(person)
        for person in dead:
            self.icu_patients.remove(person)

    def update_status_lists(self):
        # three copies of what happens in group for the three lists of people
        # in the hospital
        super().update_status_lists()
        self.update_status_lists_for_patients()
        self.update_status_lists_for_ICUpatients()
        ic_logger.info(
            "=== update status list for hospital with ", self.size, " people ==="
        )
        ic_logger.info(
            "=== hospital currently has ",
            len(self.patients),
            " patients",
            "and ",
            len(self.icu_patients),
            " ICU patients",
        )


class Hospitals:
    def __init__(self, hospital_df: pd.DataFrame, config: dict, box_mode: bool = False):
        """
        Create a group of hospitals, and provide functionality to  llocate patients to a nearby hospital

        Parameters
        ----------
        hospital_df:
            data frame with hospital data
        config:
            config dictionary
        box_mode:
            whether to run in single box mode, or full simulation
        """
        self.box_mode = box_mode
        self.members = []
        self.max_distance = config["max_distance"]
        self.icu_fraction = config["icu_fraction"]
        if not self.box_mode:
            ic_logger.info("There are %d hospitals in the world." % len(hospital_df))
            self.init_hospitals(hospital_df)
            self.init_trees(hospital_df)
        else:
            self.members.append(Hospital(1, 10, 2, None))
            self.members.append(Hospital(2, 5000, 5000, None))

    @classmethod
    def from_file(
        cls, filename: str, config_filename: str, box_mode: bool = False
    ) -> "Hospitals":
        """
        Initialize Hospitals from path to data frame, and path to config file 

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
        return Hospitals(hospital_df, config, box_mode=box_mode)

    def init_hospitals(self, hospital_df: pd.DataFrame):
        """
        Create Hospital objects with the right characteristics, 
        as given by dataframe

        Parameters
        ----------
        hospital_df:
            dataframe with hospital characteristics data

        """
        hospitals = []
        for i, (index, row) in enumerate(hospital_df.iterrows()):
            n_beds = row["beds"]
            n_icu_beds = round(self.icu_fraction * n_beds)
            n_beds -= n_icu_beds
            msoa_name = row["MSOA"]
            coordinates = row[["Latitude", "Longitude"]].values
            # create hospital
            hospital = Hospital(i, n_beds, n_icu_beds, coordinates, msoa_name,)
            hospitals.append(hospital)
        self.members = hospitals

    def init_trees(self, hospital_df: pd.DataFrame) -> BallTree:
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
            np.deg2rad(hospital_df[["Latitude", "Longitude"]].values),
            metric="haversine",
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

        if self.box_mode:
            for hospital in self.members:
                if tag and not (hospital.full):
                    return hospital
                if tagICU and not (hospital.full_ICU):
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
                if (
                    person.health_information.tag == "intensive care"
                    and not (hospital.full)
                ) or (
                    person.health_information.tag == "hospitalised"
                    and not (hospital.full_ICU)
                ):
                    break
            if hospital is not None:
                ic_logger.info(
                    f"Receiving hospital for patient with {person.health_information.tag} at distance = {distance} km"
                )
                hospital.add_as_patient(person)
            else:
                ic_logger.info(
                    "no hospital found for patient with",
                    person.health_information.tag,
                    "in distance < ",
                    self.max_distance,
                    " km.",
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


if __name__ == "__main__":

    Hospitals.from_file(
        "~/covidmodelling/data/processed/hospital_data/england_hospitals.csv",
        "/home/florpi/covidmodelling/configs/defaults/hospitals.yaml",
    )
