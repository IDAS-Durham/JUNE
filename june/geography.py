import os
import csv
import logging
import pathlib
from pathlib import Path
from random import randint
from itertools import chain, count
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

from june import get_creation_logger

default_data_path_1 = Path(os.path.abspath(__file__)).parent.parent / \
    "data/census_data/area_code_translations"
default_data_path_2 = Path(os.path.abspath(__file__)).parent.parent / \
    "data/processed/geographical_data"
default_logging_config_filename = Path(__file__).parent.parent / \
    "configs/config_world_creation_logger.yaml"

logger = logging.getLogger(__name__)


class Area:
    """
    Fine geographical resolution.
    """
    _id = count()
    
    def __init__(
            self,
            name: str,
            super_area: "SuperArea" = None,
            coordinates: [float, float] = [None, None],
    ):
        """
        """
        self.id = next(self._id)
        self.name = name


class Areas:
    def __init__(self, areas: List[Area]):
        self.members = areas
       
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
            area: List[Area] = [None],
            coordinates: [float, float] = [None, None],
    ):
        self.id = next(self._id)
        self.name = name
        self.area = area


class SuperAreas:
    def __init__(self, super_areas: List[SuperArea]):
        self.members = super_areas
       
    def __len__(self):
        return len(self.members)

    def __iter__(self):
        return iter(self.members)


class Geography:
    def __init__(
            self,
            hierarchy: pd.DataFrame,
            units_coordinate: dict, 
    ):
        """
        Generate hierachical devision of geography.

        Parameters
        ----------
        hierarchy
            The different geographical division units from which the
            hierachical structure will be constructed.
        coordinates

        Note: It would be nice to find a better way to handle coordinates.
        """
        self.hierarchy = hierarchy
        self.hierarchy = _sorting_and_grouping(self.hierarchy)
        self.units_coordinate = units_coordinate
        self.create_geographical_units()

    def create_geographical_units(self):
        """
        Create geo-graph of the used geographical units.

        Note: This function looks a bit more complicated than need be,
        but it was created with a eye on the future.
        """
        areas_list = [] 
        super_areas_list = []

        # loop through all but the smallest geo-unit
        for geo_unit_level in range(self.hierarchy.index.nlevels):  #Atm. only one level
            geo_units_labels = self.hierarchy.index.get_level_values(
                geo_unit_level
            ).unique()
            
            # loop through this geo-unit
            for unit_label in geo_units_labels:
                smaller_unit_df = self.hierarchy.loc[unit_label]
                superarea_areas_list = []

                # loop over smallest geo-unit
                for smaller_unit_label in smaller_unit_df.values[0].split(' '):
                     
                    superarea_areas_list.append(
                        Area(
                            name=smaller_unit_label,
                            coordinates=self.get_unit_coord(
                                smaller_unit_df.index.values[0],
                                smaller_unit_label,
                            ),
                        )
                    )
                
                areas_list.append(superarea_areas_list)
                super_area = SuperArea(
                    name=unit_label,
                    coordinates=self.get_unit_coord(
                        geo_units_labels.name,
                        unit_label,
                    ),
                    area=superarea_areas_list,
                )
                for area in superarea_areas_list:
                    area.super_area = super_area
                super_areas_list.append(super_area)
       
        self.areas = Areas(
            list(chain.from_iterable(areas_list))
        )
        self.super_areas = SuperAreas(super_areas_list)
        del superarea_areas_list, areas_list, super_areas_list

    def get_unit_coord(self, unit, name) -> list:
        """
        Read two numbers from input df, return as array.

        Parameters
        ----------
        unit
            Geographical units (e.g. OA, MSOA)
        name
            Name of the selected member of a unit (e.g. E02000001)
        """
        # NOTE df["X"] ~5 times faster than df[ ["Y", "X"] ]
        return [
            self.units_coordinate[unit][name]['Y'],
            self.units_coordinate[unit][name]['X'],
        ]
    
    def get_super_area_coord(self, area_name):
        """
        Read two numbers from input df, return as array.
        """
    #    oa = pd.read_csv('./../data/geographical_data/oa_coorindates.csv')
    #    oa_msoa = pd.read_csv(
    #        './../data/census_data/area_code_translations/oa_msoa_englandwales_2011.csv'
    #    )
        #oa_msoa_ll = pd.merge(oa_msoa, oa, on='OA11CD')
        #oa_msoa_ll_mean = oa_msoa_ll.groupby('MSOA11CD', as_index=False)[['X','Y']].mean()
        #oa_msoa_ll_mean.to_csv('msoa_coordinates_englandwales.csv')
        #return [df_entry["Y"], df_entry["X"]]

    @classmethod
    def from_file(
            cls,
            names_path: str = default_data_path_1,
            coords_path: str = default_data_path_2,
            filter_key: Optional[Dict[str, list]] = None,
            logging_config_filename: str = default_logging_config_filename,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Parameters
        ----------
        names_path
            The path to the data directory in which the names
            of areas can be found.
        coords_path
            The path to the data directory in which the coordinates
            of areas can be found.
        filter_key
            Filter out geo-units which should enter the world.
            At the moment this can only be one of [PCD, OA, MSOA]

        Note: It would be nice to find a better way to handle coordinates.
        """
        #TODO this file is missing option to filter for Region etc.
        unit_hierarchy_file = f"{names_path}/areas_mapping.csv"
        smallest_unit_coords_file = f"{coords_path}/oa_coorindates.csv"
        geo_hierarchy = _load_geo_file(unit_hierarchy_file)
        areas_coord = _load_area_coords(smallest_unit_coords_file)
        
        if filter_key is not None:
            geo_hierarchy = _filtering(geo_hierarchy, filter_key)

        # At the moment we only support data at the UK OA & MSOA level.
        geo_hierarchy = geo_hierarchy[["MSOA", "OA"]]
        
        super_areas_coord = pd.merge(areas_coord, geo_hierarchy, on='OA')
        super_areas_coord = super_areas_coord.groupby(
            'MSOA', as_index=True,
        )[['X','Y']].mean()
        
        units_coord = {
            "OA": areas_coord.T.to_dict(),
            "MSOA": super_areas_coord.T.to_dict(),
        }
        return Geography(geo_hierarchy, units_coord)


def _load_geo_file(
        names_path: str
) -> pd.DataFrame:
    """
    """
    usecols = [1,3, 4]
    column_names = ["OA", "MSOA", "LAD"]
    return pd.read_csv(
        names_path,
        names=column_names,
        usecols=usecols,
    )
    

def _load_area_coords(
        coords_path: str
) -> pd.DataFrame:
    """
    """
    usecols = [0,1,3]
    column_names = ["X", "Y", "OA"]
    return pd.read_csv(
        coords_path,
        skiprows=1,
        names=column_names,
        usecols=usecols,
    ).set_index("OA")


def _filtering(
        data: pd.DataFrame,
        filter_key: Dict[str, list],
) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[ data[list(filter_key.keys())[0]].isin(list(filter_key.values())[0]) ]


def _sorting_and_grouping(
        hierarchy: pd.DataFrame
) -> pd.DataFrame:
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
    nr_unique_units = [len(hierarchy[unit].unique())
        for unit in hierarchy.columns.values
    ]
    idx = np.argsort(np.array(nr_unique_units))
    sorted_unit_labels = list(hierarchy.columns.values[idx])
    hierarchy = hierarchy[sorted_unit_labels]

    # grouping
    hierarchy = hierarchy.groupby(sorted_unit_labels[:-1], as_index=True)
    hierarchy = hierarchy.agg(lambda x : ' '.join(x))
    return hierarchy

if __name__ == "__main__":
    Geography.from_file(filter_key={"MSOA": ["E02000140"]})
