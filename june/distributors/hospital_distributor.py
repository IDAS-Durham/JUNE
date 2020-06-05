import logging

import numpy as np
import yaml
from scipy import stats

from june import paths
from june.demography.geography import SuperAreas, SuperArea
from june.groups import Hospitals

logger = logging.getLogger(__name__)

default_config_filename = (
        paths.configs_path
        / "defaults/distributors/hospital_distributor.yaml"
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
        self.medic_min_age = config["medic_min_age"]
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
        for super_area in super_areas:
            self.distribute_medics_to_hospitals(super_area)

    def get_hospitals_in_super_area(self, super_area: SuperArea):
        """
        """
        hospitals_in_super_area = [
            hospital
            for hospital in self.hospitals.members
            if hospital.super_area == super_area
        ]
        return hospitals_in_super_area

    def distribute_medics_to_hospitals(self, super_area):
        """
        Healthcares sector
            2211: Medical practitioners
            2217: Medical radiographers
            2231: Nurses
            2232: Midwives
        We put a lower bound on the age of medics to be 25.
        """
        hospitals_in_super_area = self.get_hospitals_in_super_area(super_area)
        if len(hospitals_in_super_area) == 0:
            return
        medics = [
            person
            for idx, person in enumerate(super_area.workers)
            if person.sector == self.healthcare_sector_label and person.age > self.medic_min_age
        ]
        if len(medics) == 0:
            logger.info(f"\n The SuperArea {super_area.name} has no people that work in it!")
            return
        else:
            # equal chance to work in any hospital nearest to any area within msoa
            # Note: doing it this way rather then putting them into the area which
            # is currently chose in the for-loop in the world.py file ensure that
            # medics are equally distr., no over-crowding
            areas_rv = stats.rv_discrete(
                values=(
                    np.arange(len(hospitals_in_super_area)),
                    np.array([1 / len(hospitals_in_super_area)] * len(hospitals_in_super_area)),
                )
            )
            hospitals_rnd_arr = areas_rv.rvs(size=len(medics))

            for i, medic in enumerate(medics):
                if medic.sub_sector is not None:
                    hospital = hospitals_in_super_area[hospitals_rnd_arr[i]]
                    # if (hospital.n_medics < hospital.n_medics_max):# and \
                    hospital.add(medic, hospital.SubgroupType.workers)
