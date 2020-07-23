import datetime
from typing import Union, Optional, List, Dict

from .policy import Policy, Policies, PolicyCollection
from june.groups import Hospitals, Hospital, MedicalFacilities, MedicalFacility
from june.demography import Person
from june.infection.symptom_tag import SymptomTag

hospitalised_tags = (SymptomTag.hospitalised, SymptomTag.intensive_care)


class MedicalCarePolicy(Policy):
    def __init__(self, start_time="1900-01-01", end_time="2500-01-01"):
        super().__init__(start_time, end_time)
        self.policy_type = "medical_care"

    def is_active(self, date: datetime.datetime) -> bool:
        return True


class MedicalCarePolicies(PolicyCollection):
    policy_type = "medical_care"

    def apply(self, person: Person, medical_facilities, days_from_start: float):
        for policy in self.policies:
            policy.apply(person, medical_facilities, days_from_start)


class Hospitalisation(MedicalCarePolicy):
    """
    Hospitalisation policy. When applied to a sick person, allocates that person to a hospital, if the symptoms are severe
    enough. When the person recovers, releases the person from the hospital.
    """

    def apply(
        self,
        person: Person,
        medical_facilities: List[MedicalFacilities],
        days_from_start: float,
    ):
        hospitals = [
            medical_facility
            for medical_facility in medical_facilities
            if isinstance(medical_facility, Hospitals)
        ][0]
        if person.health_information.recovered:
            if person.medical_facility is not None and isinstance(
                person.medical_facility.group, Hospital
            ):
                person.medical_facility.group.release_as_patient(person)
            return
        symptoms_tag = person.health_information.tag
        if symptoms_tag in hospitalised_tags :
            if person.medical_facility is None:
                hospitals.allocate_patient(person)
            elif not isinstance(person.medical_facility.group, Hospital):
                try:
                    person.medical_facility.remove(person)
                except:
                    pass
                hospitals.allocate_patient(person)
            else:
                if person.health_information.tag == SymptomTag.hospitalised:
                    person.subgroups.medical_facility = person.medical_facility.group[
                        person.medical_facility.group.SubgroupType.patients
                    ]
                elif person.health_information.tag == SymptomTag.intensive_care:
                    person.subgroups.medical_facility = person.medical_facility.group[
                        person.medical_facility.group.SubgroupType.icu_patients
                    ]
                else:
                    raise ValueError(
                        f"Person with health information {person.health_information.tag} cannot go to hospital."
                    )
