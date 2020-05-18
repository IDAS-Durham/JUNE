import logging
from enum import IntEnum
from typing import List
import numpy as np
import h5py

import pandas as pd

from june import paths
from june.groups.group import Group, Supergroup

default_data_path = (
    paths.data_path / "processed/census_data/output_area/EnglandWales/carehomes.csv"
)
nan_integer = -999

logger = logging.getLogger(__name__)


class CareHome(Group):
    """
    The Carehome class represents a carehome and contains information about 
    its residents, workers and visitors.
    We assume three subgroups:
    0 - workers
    1 - residents 
    2 - visitors 
    """
    __slots__ = "n_residents", "area"

    class SubgroupType(IntEnum):
        workers = 0
        residents = 1
        visitors = 2

    def __init__(self, area, n_residents):
        super().__init__()
        self.n_residents = n_residents
        self.area = area

    def add(
        self, person, subgroup_type=SubgroupType.residents,
    ):
        super().add(
            person,
            activity_type=person.ActivityType.residence,
            subgroup_type=subgroup_type,
        )

    @property
    def workers(self):
        return self.subgroups[self.SubgroupType.workers]

    @property
    def residents(self):
        return self.subgroups[self.SubgroupType.residents]

    @property
    def visitors(self):
        return self.subgroups[self.SubgroupType.visitors]


class CareHomes(Supergroup):
    __slots__ = "members"

    def __init__(self, care_homes: List[CareHome]):
        super().__init__()
        self.members = care_homes

    @classmethod
    def for_geography(cls, geography, data_filename: str = default_data_path):
        """
        Initializes care homes from geography.
        """
        care_home_df = pd.read_csv(data_filename, index_col=0)
        area_names = [area.name for area in geography.areas]
        care_home_df = care_home_df.loc[area_names]
        care_homes = []
        logger.info(f"There are {len(care_home_df)} care_homes in this geography.")
        for area in geography.areas:
            n_residents = care_home_df.loc[area.name].values[0]
            if n_residents != 0:
                area.care_home = CareHome(area, n_residents)
                care_homes.append(area.care_home)
        return cls(care_homes)

    def to_hdf5(self, file_path: str): 
        n_carehomes = len(self.members)
        ids = []
        areas = []
        n_residents = []
        for carehome in self.members:
            ids.append(carehome.id)
            if carehome.area is None:
                areas.append(nan_integer)
            else:
                areas.append(carehome.area.id)
            n_residents.append(carehome.n_residents)

        ids = np.array(ids, dtype=np.int)
        areas = np.array(areas, dtype=np.int)
        n_residents = np.array(n_residents, dtype=np.float)
        with h5py.File(file_path, "w") as f:
            people_dset = f.create_group("care_homes")
            people_dset.attrs["n_care_homes"] = n_carehomes
            people_dset.create_dataset("id", data=ids)
            people_dset.create_dataset("area", data=areas)
            people_dset.create_dataset("n_residents", data=n_residents)

    @classmethod
    def from_hdf5(cls, file_path: str):
        with h5py.File(file_path, "r") as f:
            carehomes = f["care_homes"]
            carehomes_list = list()
            chunk_size = 50000
            n_carehomes = carehomes.attrs["n_care_homes"]
            n_chunks = int(np.ceil(n_carehomes / chunk_size))
            for chunk in range(n_chunks):
                idx1 = chunk * chunk_size
                idx2 = min((chunk + 1) * chunk_size, n_carehomes)
                ids = carehomes["id"]
                areas = carehomes["area"][idx1:idx2]
                n_residents = carehomes["n_residents"][idx1:idx2]
                for k in range(idx2 - idx1):
                    area = areas[k]
                    if area == nan_integer:
                        area = None
                    carehome = CareHome(area, n_residents[k])
                    carehome.id = ids[k]
                    carehomes_list.append(carehome)
        return cls(carehomes_list)
