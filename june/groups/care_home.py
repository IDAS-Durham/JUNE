import logging
import yaml
import random
from enum import IntEnum
from typing import List
import numpy as np

import pandas as pd

from june import paths
from june.epidemiology.infection.disease_config import DiseaseConfig
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
    Represents a care home with its residents, workers, and visitors.

    Parameters
    ----------
    area : Area
        The area the care home belongs to.
    n_residents : int
        The number of residents in the care home.
    n_workers : int
        The number of workers in the care home.
    disease_config : DiseaseConfig
        The disease configuration object.
    """

    __slots__ = ("n_residents", "area", "n_workers", "quarantine_starting_date", "registered_members_ids")

    def __init__(
        self,
        area: Area = None,
        n_residents: int = None,
        n_workers: int = None,
        registered_members_ids: dict = None,
    ):
        super().__init__()
        self.n_residents = n_residents
        self.n_workers = n_workers
        self.area = area
        self.quarantine_starting_date = None
        self.registered_members_ids = registered_members_ids if registered_members_ids is not None else {}

    def add(self, person, subgroup_type, activity: str = "residence"):
        if activity == "leisure":
            super().add(
                person, subgroup_type=self.SubgroupType.visitors, activity="leisure"
            )
        else:
            super().add(person, subgroup_type=subgroup_type, activity=activity)
            
    def add_to_registered_members(self, person_id, subgroup_type=0):
        """
        Add a person to the registered members list for a specific subgroup.
        
        Parameters
        ----------
        person_id : int
            The ID of the person to add
        subgroup_type : int, optional
            The subgroup to add the person to (default: 0)
        """
        # Create the subgroup if it doesn't exist
        if subgroup_type not in self.registered_members_ids:
            self.registered_members_ids[subgroup_type] = []
            
        # Add the person if not already in the list
        if person_id not in self.registered_members_ids[subgroup_type]:
            self.registered_members_ids[subgroup_type].append(person_id)

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

    @property
    def type(self):
        return "care_home"


class CareHomes(Supergroup):
    venue_class = CareHome

    def __init__(self, care_homes: List[venue_class]):
        super().__init__(members=care_homes)

    @classmethod
    def for_geography(
        cls,
        geography: Geography,
        data_file: str = default_data_filename,
    ) -> "CareHomes":
        """
        Initializes care homes from geography using a disease configuration.

        Parameters
        ----------
        geography : Geography
            The geography object with areas for initializing care homes.
        disease_config : DiseaseConfig
            The disease configuration object containing relevant settings.
        data_file : str
            Path to the care home data file.

        Returns
        -------
        CareHomes
            An instance containing all created care homes.
        """
        areas = geography.areas
        if not areas:
            raise CareHomeError("Empty geography!")
        return cls.for_areas(areas, data_file)
    
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
                area.care_home = cls.venue_class(area, n_residents, n_worker)
                care_homes.append(area.care_home)

        # Visualization - Sample 5 care homes for inspection
        sample_care_homes = [
            {
                "| Care Home ID": care_home.id,
                "| Area": care_home.area.name if care_home.area else "Unknown",
                "| Residents Needed": care_home.n_residents,
                "| Workers Needed": care_home.n_workers,  # Use the corrected attribute name
                "| Coordinates": care_home.coordinates if care_home.area else "Unknown",
            }
            for care_home in random.sample(care_homes, min(5, len(care_homes)))
        ]

        df_care_homes = pd.DataFrame(sample_care_homes)
        print("\n===== Sample of Created Care Homes =====")
        print(df_care_homes)
        return cls(care_homes)
