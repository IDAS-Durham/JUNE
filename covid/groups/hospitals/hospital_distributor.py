import warnings
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

    def __init__(self, hospitals, msoarea):
        self.world = hospitals.world
        self.msoarea = msoarea
        # check if this msoarea has hospitals
        self.hospitals_in_msoa(hospitals)
        if len(self.msoarea.hospitals) == 0:
            pass
        else:
            self.healthcare_sector_label = (
                self.world.config["companies"]["key_sector"]["hospitals"]
            )
            patience_nr_per_nurse = self.world.config["hospitals"]["patience_nr_per_nurse"]
            patience_nr_per_doctor = self.world.config["hospitals"]["patience_nr_per_doctor"]
            self.hospitals_in_msoa(hospitals)
            self.distribute_medics_to_hospitals()

    def hospitals_in_msoa(self, hospitals):
        """
        """
        hospitals_in_msoa = [
            hospital
            for hospital in hospitals.members
            if hospital.msoa_name is self.msoarea.name
        ]
        self.msoarea.hospitals = hospitals_in_msoa

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
            warnings.warn(
                f"\n The MSOArea {0} has no people that work in it!".format(self.msoarea.name),
                RuntimeWarning
            )
        
        else:
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
                if medic.industry_specific != None:
                    hospital = hospitals_in_msoa[hospitals_rnd_arr[i]]
                        
                    if (hospital.n_medics < hospital.n_medics_max):# and \
                        medic.hospital = hospital.id
                        hospital.n_medics += 1
