import numpy as np
from random import uniform
from scipy import stats
import warnings


class HospitalError(BaseException):
    """ class for throwing hospital related errors """
    pass


class HospitalDistributor:
    """
    Distributes people working in health-care to hospitals
    """

    def __init__(self, companies, msoarea):
        self.world = world
        self.msoarea = msoarea
        self.companies = companies
        self.healthcare_sector_label = (
            self.world.config["companies"]["key_sector"]["hospitals"]
        )
        patience_nr_per_nurse = self.world.config["hospitals"]["patience_nr_per_nurse"]
        patience_nr_per_doctor = self.world.config["hospitals"]["patience_nr_per_doctor"]

    def distribute_medics_to_hospitals(self):
        """
        Healthcares sector
            2211: Medical practitioners
            2217: Medical radiographers
            2231: Nurses
            2232: Midwives
        """

        medics = [
            person for idx,person in enumerate(self.msoarea.work_people)
            if person.industry == self.healthcare_sector_label
        ]

        if len(medics) == 0:
            raise HouseholdError(
                f"\n The MSOArea {0} has no people that work in it!".format(msoarea.id)
            )

        # equal chance to work in any hospital nearest to any area within msoa
        # Note: doing it this way rather then putting them into the area which
        # is currently chose in the for-loop in the world.py file ensure that
        # medics are equally distr., no over-crowding
        hospitals_in_msoa = self.msoarea.hospitals
        areas_rv = stats.rv_discrete(
            values=(
                np.arange(len(hospitals_in_msoa)),
                np.array([1/len(hospitals_in_msoa)]*len(hospitals_in_msoa))
            )
        )
        hospitals_rnd_arr = areas_rv.rvs(size=len(medics))

        for i,medic in enumerate(medics):
            if medics.industry_specific != None:
                hospital = hospitals_in_msoa[hospitals_rnd_arr[i]]
                    
                if (hospital.n_medics < hospital.n_medics_max):# and \
                    medic.hospital = hospital.id
                    hospital.n_medics += 1
