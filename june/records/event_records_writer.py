import tables
import numpy as np
from june.records.helper_records_writer import _get_description_for_event


class EventRecord:
    def __init__(self, hdf5_file, table_name, int_names, float_names, str_names):
        if not isinstance(hdf5_file, tables.file.File):
            raise TypeError("hdf5_file must be an open HDF5 file (use tables.openFile)")
        self.file = hdf5_file
        self.table_name = table_name
        self.int_names = int_names
        self.float_names = float_names
        self.str_names = str_names
        self.attributes = int_names + float_names + str_names
        for attribute in self.attributes:
            setattr(self, attribute, [])
        self._create_table(int_names, float_names, str_names)

    def _create_table(self, int_names, float_names, str_names):
        table_description = _get_description_for_event(
            int_names=int_names,
            float_names=float_names,
            str_names=str_names,
            timestamp=True,
        )
        self.table = self.file.create_table(
            self.file.root, self.table_name, table_description
        )

    @property
    def number_of_events(self):
        return len(getattr(self, self.attributes[0]))

    def accumulate(self):
        pass

    def record(self, hdf5_file, timestamp: str):
        data = np.rec.fromarrays(
            [
                np.array(
                    [timestamp.strftime("%Y-%m-%d")] * self.number_of_events,
                    dtype="S10",
                )
            ]
            + [np.array(getattr(self, name), dtype=np.int32) for name in self.int_names]
            + [
                np.array(getattr(self, name), dtype=np.float32)
                for name in self.float_names
            ]
            + [np.array(getattr(self, name), dtype="S20") for name in self.str_names]
        )

        table = getattr(hdf5_file.root, self.table_name)
        table.append(data)
        table.flush()
        for attribute in self.attributes:
            setattr(self, attribute, [])


class InfectionRecord(EventRecord):
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="infections",
            int_names=["location_ids", "infected_ids"],
            float_names=[],
            str_names=["location_specs"],
        )

    def accumulate(self, location_spec, location_id, infected_id):
        self.location_specs.append(location_spec)
        self.location_ids.append(location_id)
        self.infected_ids.append(infected_id)


class HospitalAdmissionsRecord(EventRecord):
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="hospital_admissions",
            int_names=["hospital_ids", "patient_ids"],
            float_names=[],
            str_names=[],
        )

    def accumulate(self, hospital_id, patient_id):
        self.hospital_ids.append(hospital_id)
        self.patient_ids.append(patient_id)


class ICUAdmissionsRecord(EventRecord):
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="icu_admissions",
            int_names=["hospital_ids", "patient_ids"],
            float_names=[],
            str_names=[],
        )

    def accumulate(self, hospital_id, patient_id):
        self.hospital_ids.append(hospital_id)
        self.patient_ids.append(patient_id)


class DeathsRecord(EventRecord):
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="deaths",
            int_names=["location_ids", "dead_person_ids"],
            float_names=[],
            str_names=["location_specs"],
        )

    def accumulate(self, location_spec, location_id, dead_person_id):
        self.location_specs.append(location_spec)
        self.location_ids.append(location_id)
        self.dead_person_ids.append(dead_person_id)


class RecoveriesRecord(EventRecord):
    def __init__(
        self, hdf5_file,
    ):
        super().__init__(
            hdf5_file=hdf5_file,
            table_name="recoveries",
            int_names=["recovered_person_ids"],
            float_names=[],
            str_names=[],
        )

    def accumulate(self, recovered_person_id):
        self.recovered_person_ids.append(recovered_person_id)
