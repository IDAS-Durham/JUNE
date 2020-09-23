import tables
import numpy as np
from june.records.helper_records_writer import _get_description_for_event

class StaticRecord:
    def __init__(self, hdf5_file, table_name, int_names, float_names):
        if not isinstance(hdf5_file, tables.file.File):
            raise TypeError("hdf5_file must be an open HDF5 file (use tables.openFile)")
        self.file = hdf5_file
        self.table_name = table_name
        self.int_names = int_names
        self.float_names = float_names
        self.attributes = int_names + float_names
        for attribute in self.attributes:
            setattr(self, attribute, [])
        self._create_table(int_names, float_names)

    def _create_table(self, int_names, float_names):
        table_description = _get_description_for_event(
            int_names=int_names, float_names=float_names, timestamp=False
        )
        self.table = self.file.create_table(
            self.file.root, self.table_name, table_description
        )

    def record_in_chunks(self, hdf5_file):


