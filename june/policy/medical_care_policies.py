import datetime
from typing import Union, Optional, List, Dict

from .policy import Policy
from june.groups import Hospitals
from june.demography import Person


class MedicalCarePolicy(Policy):
    def __init__(self):
        super().__init__(start_time="1900-01-01", end_time="2500-01-01")
        self.policy_type = "medical_care"

    def is_active(self, date: datetime.datetime) -> bool:
        return True

class MedicalCarePolicies(MedicalCarePolicy):
    def __init__(self, policies: List[MedicalCarePolicy]):
        super().__init__(policies=policies)

    def apply(self, person: Person):
        for policy in self.policies:
            policy.apply(person)


class Hospitalisation(MedicalCarePolicy):
    def __init__(self, hospitals: Hospitals):
        """
        Hospitalisation policy. When applied to a sick person, allocates that person to a hospital, if the symptoms are severe
        enough. When the person recovers, releases the person from the hospital.
        """
        super().__init__()
        self.hospitals = hospitals

    def apply(self, person: Person):
        if person.health_information.recovered:
            person.medical_facility.group.release_as_patient(person)
            return
        if person.medical_facility is None:
            self.hospitals.allocate_patient(person)
        elif person.health_information.tag == "hospitalised":
            person.subgroups.medical_facility = person.medical_facility.group[
                person.hospital.SubgroupType.patients
            ]
        elif person.health_information == "intensive_care":
            person.subgroups.hospital = person.hospital.group[
                person.hospital.SubgroupType.icu_patients
            ]
        else:
            raise ValueError(
                f"Person with health information {person.health_information} cannot go to hospital."
            )

