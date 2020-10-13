import datetime
from typing import List, Optional
from june.groups import Hospitals, Hospital, MedicalFacilities, MedicalFacility

from .policy import Policy, Policies, PolicyCollection
from june.groups import Hospitals, Hospital, ExternalSubgroup
from june.demography import Person
from june.infection.symptom_tag import SymptomTag
from june.records import Record

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

    def apply(
        self,
        person: Person,
        medical_facilities,
        days_from_start: float,
        record: Optional[Record],
    ):
        """
        Applies medical care policies. Hospitalisation takes preference over all.
        """
        hospitalisation_policies = [
            policy for policy in self.policies if isinstance(policy, Hospitalisation)
        ]
        for policy in hospitalisation_policies:
            activates = policy.apply(person=person, record=record)
            if activates:
                return
        for policy in [
            policy for policy in self.policies if policy not in hospitalisation_policies
        ]:
            activates = policy.apply(person, medical_facilities, days_from_start)
            if activates:
                return


class Hospitalisation(MedicalCarePolicy):
    """
    Hospitalisation policy. When applied to a sick person, allocates that person to a hospital, if the symptoms are severe
    enough. When the person recovers, releases the person from the hospital.
    """

    def __init__(
        self,
        start_time="1900-01-01",
        end_time="2500-01-01",
        probability_of_care_home_resident_admission=0.3,
    ):
        super().__init__(start_time, end_time)
        self.probability_of_care_home_resident_admission = (
            probability_of_care_home_resident_admission
        )

    def apply(
        self,
        person: Person,
        record: Optional[Record] = None,
    ):
        symptoms_tag = person.infection.tag
        if symptoms_tag in hospitalised_tags:
            if person.medical_facility is not None:
                patient_hospital = person.medical_facility.group
            else:
                patient_hospital = person.super_area.closest_hospitals[0]
            # note, we dont model hospital capacity here.
            status = patient_hospital.allocate_patient(
                person,
            )
            if record is not None:
                if status in [
                    "ward_admitted"
                ]:  # TODO: think if we want to count transfers as admissions.
                    record.accumulate(
                        table_name="hospital_admissions",
                        hospital_id=patient_hospital.id,
                        patient_id=person.id,
                    )
                elif status in ["icu_admitted"]:
                    record.accumulate(
                        table_name="icu_admissions",
                        hospital_id=patient_hospital.id,
                        patient_id=person.id,
                    )
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
                person.medical_facility.group.release_patient(person)
            return
