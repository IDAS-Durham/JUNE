from enum import IntEnum
import pandas as pd
from pathlib import Path

from june.groups.group import Group
from june.logger_creation import logger
from enum import IntEnum
from typing import List

default_data_path = (
    Path(__file__).parent.parent.parent
    / "data/processed/census_data/output_area/EnglandWales/carehomes.csv"
)


class CareHome(Group):
    """
    The Carehome class represents a carehome and contains information about 
    its residents, workers and visitors.
    We assume three subgroups:
    0 - workers
    1 - residents 
    2 - visitors 
    """

    spec = "carehome"


    class GroupType(IntEnum):
        workers = 0
        residents = 1
        visitors = 2

    def __init__(self, area, n_residents):
        super().__init__()
        self.n_residents = n_residents
        self.area = area

    def add(self, person, qualifier=GroupType.residents):
        super().add(person, qualifier)
        person.groups.append(self)

class CareHomes:
    __slots__ = "members"

    def __init__(self, carehomes: List[CareHome]):
        self.members = carehomes

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    @classmethod
    def for_geography(cls, geography, data_filename: str = default_data_path):
        """
        Initializes carehomes from geography.
        """
        carehome_df = pd.read_csv(data_filename, index_col=0)
        area_names = [area.name for area in geography.areas]
        carehome_df = carehome_df.loc[area_names]
        carehomes = []
        for area in geography.areas:
            n_residents = carehome_df.loc[area.name].values[0]
            if n_residents != 0:
                area.carehome = CareHome(area, n_residents)
                carehomes.append(area.carehome)
        return cls(carehomes)
