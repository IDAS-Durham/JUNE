import logging

import numpy as np
from random import shuffle
import yaml
from typing import List, Optional

from june import paths
from june.geography import SuperAreas, SuperArea
from june.groups import Hospitals

logger = logging.getLogger("hospital_distributor")

default_config_filename = (
    paths.configs_path / "defaults/distributors/hospital_distributor.yaml"
)


class HospitalDistributor:
    """
    Distributes people to work as health care workers in hospitals
        
        #TODO: sub sectors of doctors and nurses should be found
        Healthcares sector
        2211: Medical practitioners
        2217: Medical radiographers
        2231: Nurses
        2232: Midwives
    """

    def __init__(
        self,
        hospitals: Hospitals,
        medic_min_age: int,
        patients_per_medic: int,
        healthcare_sector_label: Optional[str] = None,
    ):
        """
        
        Parameters
        ----------
        hospitals:
            hospitals to populate with workers
        medic_min_age:
            minimum age to qualify as a worker
        patients_per_medic:
            ratio of patients per medic
        healthcare_sector_label:
            string that characterizes the helathcare workers
        """
        # check if this msoarea has hospitals
        self.hospitals = hospitals
        self.medic_min_age = medic_min_age
        self.patients_per_medic = patients_per_medic
        self.healthcare_sector_label = healthcare_sector_label

    @classmethod
    def from_file(
        cls, hospitals, config_filename=default_config_filename,
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return HospitalDistributor(
            hospitals=hospitals,
            medic_min_age=config["medic_min_age"],
            patients_per_medic=config["patients_per_medic"],
            healthcare_sector_label=config["healthcare_sector_label"],
        )

    def distribute_medics_from_world(self, people: List["Person"]):
        """
        Randomly distribute people from the world to work as medics for hospitals,
        useful if we don't have data on where do people work. It will still
        match the patients to medic ratio and the minimum age to be a medic.

        Parameters
        ----------
        people:
            list of Persons in the world
        """
        medics = [person for person in people if person.age >= self.medic_min_age]
        shuffle(medics)
        for hospital in self.hospitals:
            max_capacity = hospital.n_beds + hospital.n_icu_beds
            if max_capacity == 0:
                continue
            n_medics = max(int(np.floor(max_capacity / self.patients_per_medic)), 1)
            for _ in range(n_medics):
                medic = medics.pop()
                hospital.add(medic, hospital.SubgroupType.workers)
                medic.lockdown_status = "key_worker"

    def distribute_medics_to_super_areas(self, super_areas: SuperAreas):
        """
        Distribute medics to super areas, flow data is necessary to find medics in the 
        super area according to their sector.

        Parameters
        ----------
        super_areas:
            object containing all the super areas to distribute medics
        """
        logger.info(f"Distributing medics to hospitals")
        for super_area in super_areas:
            self.distribute_medics_to_hospitals(super_area)
        logger.info(f"Medics distributed to hospitals")

    def get_hospitals_in_super_area(self, super_area: SuperArea) -> List["Hospital"]:
        """
        From all hospitals, filter the ones placed in a given super_area
        
        Parameters
        ----------
        super_area:
            super area 
        """
        hospitals_in_super_area = [
            hospital
            for hospital in self.hospitals.members
            if hospital.super_area.name == super_area.name
        ]
        return hospitals_in_super_area

    def distribute_medics_to_hospitals(self, super_area: SuperArea):
        """
        Distribute medics to hospitals within a super area
        Parameters
        ----------
        super_area:
            super area to distribute medics
        """
        hospitals_in_super_area = self.get_hospitals_in_super_area(super_area)
        if not hospitals_in_super_area:
            return
        medics = [
            person
            for idx, person in enumerate(super_area.workers)
            if person.sector == self.healthcare_sector_label
            and person.age > self.medic_min_age
            and person.primary_activity is None
        ]
        if not medics:
            logger.info(
                f"\n The SuperArea {super_area.name} has no people that work in it!"
            )
            return
        else:
            shuffle(medics)
            for hospital in hospitals_in_super_area:
                max_capacity = hospital.n_beds + hospital.n_icu_beds
                if max_capacity == 0:
                    continue
                n_medics = min(
                    max(int(np.floor(max_capacity / self.patients_per_medic)), 1),
                    len(medics),
                )
                for _ in range(n_medics):
                    medic = medics.pop()
                    hospital.add(medic, hospital.SubgroupType.workers)
                    medic.lockdown_status = "key_worker"

    def assign_closest_hospitals_to_super_areas(self, super_areas):
        if not self.hospitals.members:
            return
        for super_area in super_areas:
            super_area.closest_hospitals = self.hospitals.get_closest_hospitals(
                super_area.coordinates, self.hospitals.neighbour_hospitals
            )
