import numpy as np
from datetime import datetime

from june.policy import MedicalCarePolicy
from june.demography import Person
from june.infection.symptoms import SymptomTag

from camps.groups import IsolationUnits


class Isolation(MedicalCarePolicy):
    def __init__(
        self,
        start_time="1900-01-01",
        end_time="2500-01-01",
        testing_mean_time=None,
        testing_std_time=None,
        n_quarantine_days=None,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.testing_mean_time = testing_mean_time
        self.testing_std_time = testing_std_time
        self.n_quarantine_days = n_quarantine_days

    def _generate_time_from_symptoms_to_testing(self):
        return max(
            0, np.random.normal(loc=self.testing_mean_time, scale=self.testing_std_time)
        )

    def _generate_time_of_testing(self, person: Person):
        try:
            if person.health_information.time_of_symptoms_onset is not None:
                return (
                    person.health_information.time_of_symptoms_onset
                    + self._generate_time_from_symptoms_to_testing()
                )
            else:
                return np.inf
        except AttributeError:
            raise ValueError(
                f"Trying to generate time of testing for a non infected person."
            )

    def apply(
        self, person: Person, medical_facilities: IsolationUnits, days_from_start: float
    ):
        isolation_units = [
            medical_facility
            for medical_facility in medical_facilities
            if isinstance(medical_facility, IsolationUnits)
        ][0]
        if person.infected:
            if person.health_information.time_of_testing is None:
                person.health_information.time_of_testing = self._generate_time_of_testing(
                    person
                )
        if not person.hospitalised:
            if person.symptoms.tag.value >= SymptomTag.mild.value:  # mild or more
                if (
                    person.health_information.time_of_testing
                    <= days_from_start
                    <= person.health_information.time_of_testing
                    + self.n_quarantine_days
                ):
                    isolation_unit = isolation_units.get_closest()
                    isolation_unit.add(person)
