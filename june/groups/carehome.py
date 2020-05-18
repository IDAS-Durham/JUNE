import logging
from enum import IntEnum
from typing import List

import pandas as pd

from june import paths
from june.groups.group import Group, Supergroup

default_data_path = (
    paths.data_path / "processed/census_data/output_area/EnglandWales/carehomes.csv"
)

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
