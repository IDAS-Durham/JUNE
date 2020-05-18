import logging
from enum import IntEnum
from typing import List

import pandas as pd

from june import paths
from june.groups.group import Group, Supergroup

default_data_filename = (
    paths.data_path / "processed/census_data/output_area/EnglandWales/carehomes.csv"
)
default_areas_map_path = (
    paths.data_path / "processed/geographical_data/oa_msoa_region.csv"
)
default_config_filename = paths.configs_path / "defaults/groups/carehome.yaml"
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
    def for_geography(
        cls,
        geography: Geography,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "CareHomes":
        """
        Initializes care homes from geography.
        """
        area_names = [area.name for area in geography.areas]
        if len(area_names) == 0:
            raise SchoolError("Empty geography!")
        return cls.for_areas(area_names, data_file, config_file)

    @classmethod
    def for_zone(
        cls,
        filter_key: Dict[str, list],
        areas_maps_path: str = default_areas_map_path,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "CareHomes":
        """
        Initializes care homes from any available geographical unit given in
        the filter_key.
        
        Example
        -------
            filter_key = {"region" : "North East"}
            filter_key = {"msoa" : ["EXXXX", "EYYYY"]}
        """
        if len(filter_key.keys()) > 1:
            raise NotImplementedError("Only one type of area filtering is supported.")
        geo_hierarchy = pd.read_csv(areas_maps_path)
        zone_type, zone_list = filter_key.popitem()
        area_names = geo_hierarchy[geo_hierarchy[zone_type].isin(zone_list)]["oa"]
        if len(area_names) == 0:
            raise SchoolError("Region returned empty area list.")
        return cls.for_areas(area_names, data_file, config_file)


    @classmethod
    def for_areas(
        cls,
        area_names: List[str],
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
        return cls.from_file(area_names, data_file, config_file)


    @classmethod
    def from_file(
        cls,
        area_names: Optional[List[str]] = None,
        data_file: str = default_data_filename,
        config_file: str = default_config_filename,
    ) -> "CareHomes":
        """
        Initialize carehomes from path to data frame, and path to config file 

        Parameters
        ----------
        filename:
            path to school dataframe
        config_filename:
            path to school config dictionary

        Returns
        -------
        Schools instance
        """
        with open(config_file) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        care_home_df = pd.read_csv(data_file, index_col=0)
        area_names = [area.name for area in geography.areas]
        care_home_df = care_home_df.loc[area_names]
        care_homes = []
        logger.info(f"There are {len(care_home_df)} care_homes in this geography.")
        for area in geography.areas:
            n_residents = care_home_df.loc[area.name].values[0]
            n_worker = int(n_residents / worker_per_clients)
            if n_residents != 0:
                area.care_home = CareHome(area, n_residents)
                care_homes.append(area.care_home)
        return cls(care_homes)
