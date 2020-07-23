from typing import List
from june.groups import Group, Supergroup
from june.demography import Person
from june.groups.hospital import MedicalFacility, MedicalFacilities


class IsolationUnit(Group, MedicalFacility):
    def __init__(self):
        super().__init__()
    
    def add(self, person: Person):
        super().add(person=person, activity="medical_facility", subgroup_type=0)


class IsolationUnits(Supergroup, MedicalFacilities):
    def __init__(self, isolation_units: List[IsolationUnit]):
        super().__init__()
        self.members = isolation_units

    def get_closest(self):
        return self[0]

