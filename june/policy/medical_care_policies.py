import datetime
from typing import Optional

from .policy import Policy, Policies, PolicyCollection
from june.groups import Hospitals, Hospital, ExternalSubgroup
from june.demography import Person
from june.infection.symptom_tag import SymptomTag

hospitalised_tags = (SymptomTag.hospitalised, SymptomTag.intensive_care)
dead_hospital_tags = (SymptomTag.dead_hospital, SymptomTag.dead_icu)


class MedicalCarePolicy(Policy):
    def __init__(self, start_time="1900-01-01", end_time="2500-01-01"):
        super().__init__(start_time, end_time)
        self.policy_type = "medical_care"

    def is_active(self, date: datetime.datetime) -> bool:
        return True


class MedicalCarePolicies(PolicyCollection):
    policy_type = "medical_care"

    def apply(self, person: Person, medical_facilities, record: Optional["Record"]):
        for policy in self.policies:
            policy.apply(person, medical_facilities, record=record)


class Hospitalisation(MedicalCarePolicy):
    """
    Hospitalisation policy. When applied to a sick person, allocates that person to a hospital, if the symptoms are severe
    enough. When the person recovers, releases the person from the hospital.
    """

    def apply(
        self, person: Person, hospitals: Hospitals, record: Optional["Record"] = None
    ):
        symptoms_tag = person.infection.tag
        if symptoms_tag in hospitalised_tags:
            # note, we dont model hospital capacity here.
            closest_hospital = person.super_area.closest_hospitals[0]
            if record is not None and person.medical_facility is None:
                if symptoms_tag == SymptomTag.intensive_care:
                    table_name = "icu_admissions"
                else:
                    table_name = "hospital_admissions"
                record.accumulate(
                    table_name=table_name,
                    hospital_id=closest_hospital.id,
                    patient_id=person.id,
                )
            if symptoms_tag == SymptomTag.hospitalised:
                if closest_hospital.external:
                    # not in this domain, we need to send it over
                    person.subgroups.medical_facility = ExternalSubgroup(
                        group=closest_hospital,
                        subgroup_type=Hospital.SubgroupType.patients,
                    )
                else:
                    person.subgroups.medical_facility = closest_hospital.subgroups[
                        closest_hospital.SubgroupType.patients
                    ]
            else:
                if closest_hospital.external:
                    # not in this domain, we need to send it over
                    person.subgroups.medical_facility = ExternalSubgroup(
                        group=closest_hospital,
                        subgroup_type=Hospital.SubgroupType.icu_patients,
                    )
                else:
                    person.subgroups.medical_facility = closest_hospital.subgroups[
                        closest_hospital.SubgroupType.icu_patients
                    ]
        else:
            if (
                person.medical_facility is not None
                and symptoms_tag not in dead_hospital_tags
            ):
                if record is not None:
                    record.accumulate(
                        table_name="discharges",
                        hospital_id=person.medical_facility.group.id,
                        patient_id=person.id,
                    )
            return
