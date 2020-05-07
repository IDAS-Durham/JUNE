import csv
import logging
from pathlib import Path
from random import randint
from itertools import count
from typing import List, Dict, Optional


import numpy as np

from june.geography.areas import Area
from june.geography.super_areas import SuperArea
from june import get_creation_logger

default_data_path = Path(__file__).parent.parent.parent.parent / \
        "data/census_data/area_code_translations"

default_logging_config_filename = Path(__file__).parent.parent.parent.parent / \
        "configs/config_world_creation_logger.yaml"

get_creation_logger(default_logging_config_filename)
logger = logging.getLogger(__name__)


class Areas:
    def __init__(self, areas: List[Area]):
        self.members = super_areas
       
    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


class Area:
    """
    Fine geographical resolution.
    """
    _id = count()
    
    def __init__(
            self,
            name: str = None,
            coordinates: [float, float],
            super_area: str,
    ):
        """
        """
        self.id = next(self._id)


class SuperAreas:
    def __init__(self, super_areas: List[SuperArea]):
        self.members = super_areas
       
    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


class SuperArea:
    """
    Coarse geographical resolution.
    """
    _id = count()
    
    def __init__(
            self,
            name: str,
            coordinates: Optional[[float, float]] = None,
            area: List[Area],
    ):
        self.id = next(self._id)
        self.super_area = super_area
        self.area = area

        msoareas_list = []
        for msoa_name in self.msoareas.names_in_order:
            # centroid of msoa
            coordinates = ['xxx', 'xxx']
            # find postcode inside this msoarea
            pcd_in_msoa = self.area_mapping_df[
                self.area_mapping_df["MSOA"].isin([msoa_name])
            ]["PCD"].values
            # find oareas inside this msoarea
            oa_in_msoa = [
                area
                for area in self.world.areas.members
                if area.super_area == msoa_name
            ]
            # create msoarea
            msoarea = SuperArea(
                coordinates,
                oa_in_msoa,
                msoa_name,
                self.relevant_groups,
            )
            msoareas_list.append(msoarea)
            # link  area to msoarea
            for area in oa_in_msoa:
                area.super_area = msoarea
        self.msoareas.members = msoareas_list



class Geography:
    def __init__(
            self,
            hierarchy: pd.DataFrame,
    ):
        """
        Generate hierachical devision of geography.

        Parameters
        ----------
        geo_hierarchy
            The different geographical division units from which the
            hierachical structure will be constructed.
        """
        self.hierarchy = hierarchy


    def create_geographical_units(self):
        """
        Create geo-graph of the used geographical units.
        """
        for unit in self.hierarchy.columns:
            self.hierarchy[unit]

    @classmethod
    def from_file(
            cls,
            data_path: str = default_data_path,
            filter_key: Optional[Dict[str, list]] = None,
            logging_config_filename: str = default_logging_config_filename,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Parameters
        ----------
        data_path
            The path to the data directory
        filter_key
            Filter out geo-units which should enter the world.
            At the moment this can only be one of [PCD, OA, MSOA]
        """
        #TODO this file is missing option to filter for Region etc.
        geo_hierarchy_file = f"{data_path}/areas_mapping.csv"

        usecols = [1 ,3, 4]
        column_names = ["OA", "MSOA", "LAD"]
        geo_hierarchy = pd.read_csv(
            geo_hierarchy_file,
            names=column_names,
            usecols=usecols,
        )
        
        if filter_key not None:
            geo_hierarchy = _filtering(geo_hierarchy, filter_key)

        # At the moment we only support data at the UK OA & MSOA level.
        geo_hierarchy = geo_hierarchy[["MSOA", "OA"]]
        geo_hierarchy = _sorting_and_grouping(geo_hierarchy)
        return Geography(geo_hierarchy)


def _filtering(data: pd.DataFrame, filter_key: Optional[Dict[str, list]] = None):
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[ data[filter_key["unit"]].isin(filter_key["names"]) ]


def _sorting_and_grouping(self, hierarchy: pd.DataFrame):
    """
    Find the order for available geographical units from fine (left column)
    to coarse (right column) granular and group them.
    
    Returns
    -------
    hierarchy
        Multi-indexed DataFrame with the first index the most coarse
        and the column the smallest geographical unit.
    """
    # sorting
    nr_unique_units = [len(dic[unit].unique())
        for unit in dic.columns.values
    ]
    idx = np.argsort(np.array(nr_unique_units))
    sorted_unit_labels = list(hierarchy.columns.values[idx])
    hierarchy = hierarchy[sorted_unit_labels]

    # grouping
    hierarchy = hierarchy.groupby(sorted_unit_labels[:-1], as_index=True)
    hierarchy = hierarchy.agg(lambda x : ' '.join(x))
    return hierarchy
