from typing import Tuple, List
import pandas as pd
import numpy as np

from june.geography import Area, Geography, SuperArea, Region

class CampArea(Area):
    def __init__(
        self, name: str, super_area: "SuperArea", coordinates: Tuple[float, float],
    ):
        super().__init__(name, super_area, coordinates)
        self.pump_latrines = list()
        self.play_groups = list()
        self.shelters = list()

class CampGeography(Geography):
    def __init__(
            self, areas: List[CampArea], super_areas: List[SuperArea], regions: List[Region]
    ):
        """
        Generate hierachical devision of geography.

        Parameters
        ----------
        hierarchy
            The different geographical division units from which the
            hierachical structure will be constructed.
        area_coordinates

        Note: It would be nice to find a better way to handle coordinates.
        """
        self.areas = areas
        self.super_areas = super_areas
        self.regions = regions
        # possible buildings
        self.schools = None
        self.hospitals = None
        self.cemeteries = None
        self.shelters = None
        self.households = None

    @classmethod
    def _create_areas(
        cls, area_coords: pd.DataFrame, super_area: pd.DataFrame
    ) -> List[Area]:
        """
        Applies the _create_area function throught the area_coords dataframe.
        If area_coords is a series object, then it does not use the apply()
        function as it does not support the axis=1 parameter.

        Parameters
        ----------
        area_coords
            pandas Dataframe with the area name as index and the coordinates
            X, Y where X is longitude and Y is latitude.
        """
        # if a single area is given, then area_coords is a series
        # and we cannot do iterrows()
        if isinstance(area_coords, pd.Series):
            areas = [CampArea(area_coords.name, super_area, area_coords.values)]
        else:
            areas = []
            for name, coordinates in area_coords.iterrows():
                areas.append(
                    CampArea(
                        name,
                        super_area,
                        coordinates=np.array(
                            [coordinates.latitude, coordinates.longitude]
                        ),
                    )
                )
        return areas
