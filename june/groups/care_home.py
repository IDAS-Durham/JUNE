import logging
import yaml
from enum import IntEnum
from typing import List
import numpy as np
import h5py

import pandas as pd

from june import paths
from june.geography import Geography, Area
from june.groups import Group, Supergroup

default_data_filename = paths.data_path / "input/care_homes/care_homes_ew.csv"
default_areas_map_path = paths.data_path / "input/geography/area_super_area_region.csv"
default_config_filename = paths.configs_path / "defaults/groups/care_home.yaml"
logger = logging.getLogger("care_homes")


class CareHomeError(BaseException):
    pass


class CareHome(Group):
    """
    The Carehome class represents a carehome and contains information about
    its residents, workers and visitors.
    We assume three subgroups:
    0 - workers
    1 - residents
    2 - visitors
    """

    __slots__ = (
        "n_residents",
        "area",
        "n_workers",
        "relatives_in_care_homes",
        "relatives_in_households",
        "quarantine_starting_date",
    )

    class SubgroupType(IntEnum):
        workers = 0
        residents = 1
        visitors = 2

    def __init__(
        self, area: Area = None, n_residents: int = None, n_workers: int = None
    ):
        super().__init__()
        self.n_residents = n_residents
        self.n_workers = n_workers
        self.area = area
        self.quarantine_starting_date = None

    def add(
        self,
        person,
        subgroup_type=SubgroupType.residents,
        activity: str = "residence",
    ):
        if activity == "leisure":
            super().add(
                person,
                subgroup_type=self.SubgroupType.visitors,
                activity="leisure",
            )
        else:
            super().add(person, subgroup_type=subgroup_type, activity=activity)

    @property
    def workers(self):
        return self.subgroups[self.SubgroupType.workers]

    @property
    def residents(self):
        return self.subgroups[self.SubgroupType.residents]

    @property
    def visitors(self):
        return self.subgroups[self.SubgroupType.visitors]

    def quarantine(self, time, quarantine_days, household_compliance):
        return True

    @property
    def coordinates(self):
        return self.area.coordinates

    @property
    def super_area(self):
        if self.area is None:
            return None
        else:
            return self.area.super_area

    @property
    def households_to_visit(self):
        return None

    @property
    def care_homes_to_visit(self):
        return None

    def get_leisure_subgroup(self, person, subgroup_type, to_send_abroad):
        return self[self.SubgroupType.visitors]


class CareHomes(Supergroup):
    def __init__(self, care_homes: List[CareHome]):
        super().__init__(members=care_homes)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "CareHomes":
        """
        Initializes care homes from geography.
        """
        areas = geography.areas
        if not areas:
            raise CareHomeError("Empty geography!")
        return cls.for_areas(areas, data_file, config_file)

    @classmethod
    def for_areas(
        cls,
        areas: List[Area],
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "CareHomes":
        """
        Parameters
        ----------
        area_names
            list of areas for which to create populations
        data_path
            The path to the data directory
        config
        """
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        care_home_df = pd.read_csv(data_file, index_col=0)
        if areas:
            area_names = [area.name for area in areas]
            # filter out carehomes that are in the area of interest
            care_home_df = care_home_df.loc[area_names]
        care_homes = []
        logger.info(
            f"There are {len(care_home_df.loc[care_home_df.values!=0])} care_homes in this geography."
        )
        for area in areas:
            n_residents = care_home_df.loc[area.name].values[0]
            n_worker = max(
                int(np.ceil(n_residents / config["n_residents_per_worker"])), 1
            )
            if n_residents != 0:
                area.care_home = CareHome(area, n_residents, n_worker)
                care_homes.append(area.care_home)
        return cls(care_homes)
