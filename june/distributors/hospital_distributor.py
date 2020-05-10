import os
import logging
import yaml
from pathlib import Path
from random import uniform
from itertools import count
from typing import List, Dict, Optional
from june.groups import Hospitals
from june.geography import Geography, SuperAreas

import numpy as np
from scipy import stats

from june.logger_creation import logger

logger = logging.getLogger(__name__)

default_config_filename = (
    Path(os.path.abspath(__file__)).parent.parent.parent
    / "config/defaults/distributors/hospital_distributor.yaml"
)


class HospitalDistributor:
    """
    Distributes people working in health-care to hospitals
    """

    def __init__(
        self, hospitals: Hospitals, config_filename: str = default_config_filename
    ):
        # check if this msoarea has hospitals
        self.hospitals = hospitals
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        self.healthcare_sector_label = config["sector"]
        """
        if len(self.msoarea.hospitals) != 0:
            self.healthcare_sector_label = (
                self.world.config["companies"]["key_sector"]["hospitals"]
            )
            patience_nr_per_nurse =  self.world.config["hospitals"]["patience_nr_per_nurse"]
            patience_nr_per_doctor =  self.world.config["hospitals"]["patience_nr_per_doctor"]
            self.hospitals_in_msoa(hospitals)
            self.distribute_medics_to_hospitals()
        """

    def distribute_medics_to_super_areas(self, super_areas: SuperAreas):
        for msoa in super_areas:
            self.distribute_medics_to_hospitals_in_msoa(msoa)

    def hospitals_in_msoa(self, msoa):
        """
        """
        hospitals_in_msoa = [
            hospital
            for hospital in self.hospitals.members
            if hospital.super_area is msoa
        ]
        return hospitals_in_msoa

    def distribute_medics_to_hospitals_in_msoa(self, msoa):
        """
        Healthcares sector
            2211: Medical practitioners
            2217: Medical radiographers
            2231: Nurses
            2232: Midwives
        """
        hospitals_in_msoa = self.hospitals_in_msoa(msoa)

        medics = [
            person
            for idx, person in enumerate(msoa.work_people)
            if person.industry == self.healthcare_sector_label
        ]

        if len(medics) == 0:
            logger.info(f"\n The MSOArea {msoa.name} has no people that work in it!")

        else:
            # equal chance to work in any hospital nearest to any area within msoa
            # Note: doing it this way rather then putting them into the area which
            # is currently chose in the for-loop in the world.py file ensure that
            # medics are equally distr., no over-crowding
            areas_rv = stats.rv_discrete(
                values=(
                    np.arange(len(hospitals_in_msoa)),
                    np.array([1 / len(hospitals_in_msoa)] * len(hospitals_in_msoa)),
                )
            )
            hospitals_rnd_arr = areas_rv.rvs(size=len(medics))

            for i, medic in enumerate(medics):
                if medic.industry_specific is not None:
                    hospital = hospitals_in_msoa[hospitals_rnd_arr[i]]

                    # if (hospital.n_medics < hospital.n_medics_max):# and \
                    medic.hospital = hospital.id
                    medic.company_id = hospital.id
                    hospital.n_medics += 1
