import logging
from itertools import count, chain
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree

from june import paths
from june.demography.person import Person

default_hierarchy_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)
default_area_coord_filename = (
    paths.data_path / "input/geography/area_coordinates_sorted.csv"
)
default_superarea_coord_filename = (
    paths.data_path / "input/geography/super_area_coordinates_sorted.csv"
)
default_logging_config_filename = (
    paths.configs_path / "config_world_creation_logger.yaml"
)

logger = logging.getLogger(__name__)

earth_radius = 6371  # km


class GeographyError(BaseException):
    pass


class Area:
    """
    Fine geographical resolution.
    """

    __slots__ = (
        "people",
        "id",
        "name",
        "coordinates",
        "super_area",
        "care_home",
        "schools",
        "households",
        "social_venues",
    )
    _id = count()

    def __init__(
        self,
        name: str = None,
        super_area: "SuperArea" = None,
        coordinates: Tuple[float, float] = None,
    ):
        """
        Coordinate is given in the format [Y, X] where X is longitude and Y is latitude.
        """
        self.id = next(self._id)
        self.name = name
        self.care_home = None
        self.coordinates = coordinates
        self.super_area = super_area
        self.people = []
        self.schools = []
        self.households = []
        self.social_venues = {}

    def add(self, person: Person):
        self.people.append(person)
        person.area = self

    def populate(
        self, demography, ethnicity=True, socioecon_index=True, comorbidity=True
    ):
        for person in demography.populate(
            self.name,
            ethnicity=ethnicity,
            socioecon_index=socioecon_index,
            comorbidity=comorbidity,
        ):
            self.add(person)


class Areas:
    __slots__ = "members_by_id", "super_area", "ball_tree", "members_by_name"

    def __init__(self, areas: List[Area], super_area=None, ball_tree: bool = True):
        self.members_by_id = {area.id: area for area in areas}
        try:
            self.members_by_name = {area.name: area for area in areas}
        except AttributeError:
            self.members_by_name = None
        self.super_area = super_area
        if ball_tree:
            self.ball_tree = self.construct_ball_tree()
        else:
            self.ball_tree = None

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def get_from_id(self, id):
        return self.members_by_id[id]

    def get_from_name(self, name):
        return self.members_by_name[name]

    @property
    def members(self):
        return list(self.members_by_id.values())

    def construct_ball_tree(self):
        coordinates = np.array([np.deg2rad(area.coordinates) for area in self])
        ball_tree = BallTree(coordinates, metric="haversine")
        return ball_tree

    def get_closest_areas(self, coordinates, k=1, return_distance=False):
        coordinates = np.array(coordinates)
        if self.ball_tree is None:
            raise GeographyError("Areas initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        if return_distance:
            distances, indcs = self.ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            if coordinates.shape == (1, 2):
                areas = [self[idx] for idx in indcs[0]]
                return areas, distances[0] * earth_radius
            else:
                areas = [self[idx] for idx in indcs[:, 0]]
                return areas, distances[:, 0] * earth_radius
        else:
            indcs = self.ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            areas = [self[idx] for idx in indcs[:, 0]]
            return areas

    def get_closest_area(self, coordinates):
        return self.get_closest_areas(coordinates, k=1, return_distance=False)[0]


class SuperArea:
    """
    Coarse geographical resolution.
    """

    __slots__ = (
        "id",
        "name",
        "city",
        "coordinates",
        "closest_inter_city_station_for_city",
        "region",
        "workers",
        "areas",
        "companies",
        "closest_hospitals",
    )
    external = False
    _id = count()

    def __init__(
        self,
        name: Optional[str] = None,
        areas: List[Area] = None,
        coordinates: Tuple[float, float] = None,
        region: Optional[str] = None,
    ):
        self.id = next(self._id)
        self.name = name
        self.city = None
        self.closest_inter_city_station_for_city = {}
        self.coordinates = coordinates
        self.region = region
        self.areas = areas or []
        self.workers = []
        self.companies = []
        self.closest_hospitals = None

    def add_worker(self, person: Person):
        self.workers.append(person)
        person.work_super_area = self

    def remove_worker(self, person: Person):
        self.workers.remove(person)
        person.work_super_area = None

    @property
    def people(self):
        return list(chain.from_iterable(area.people for area in self.areas))


class SuperAreas:
    __slots__ = "members_by_id", "ball_tree", "members_by_name"

    def __init__(self, super_areas: List[SuperArea], ball_tree: bool = True):
        """
        Group to aggregate SuperArea objects.

        Parameters
        ----------
        super_areas
            list of super areas
        ball_tree
            whether to construct a NN tree for the super areas
        """
        self.members_by_id = {area.id: area for area in super_areas}
        try:
            self.members_by_name = {
                super_area.name: super_area for super_area in super_areas
            }
        except AttributeError:
            self.members_by_name = None
        if ball_tree:
            self.ball_tree = self.construct_ball_tree()
        else:
            self.ball_tree = None

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def get_from_id(self, id):
        return self.members_by_id[id]

    def get_from_name(self, name):
        return self.members_by_name[name]

    @property
    def members(self):
        return list(self.members_by_id.values())

    def construct_ball_tree(self):
        coordinates = np.array(
            [np.deg2rad(super_area.coordinates) for super_area in self]
        )
        ball_tree = BallTree(coordinates, metric="haversine")
        return ball_tree

    def get_closest_super_areas(self, coordinates, k=1, return_distance=False):
        coordinates = np.array(coordinates)
        if self.ball_tree is None:
            raise GeographyError("Areas initialized without a BallTree")
        if coordinates.shape == (2,):
            coordinates = coordinates.reshape(1, -1)
        if return_distance:
            distances, indcs = self.ball_tree.query(
                np.deg2rad(coordinates),
                return_distance=return_distance,
                k=k,
                sort_results=True,
            )
            indcs = chain.from_iterable(indcs)
            super_areas = [self[idx] for idx in indcs]
            distances = distances.flatten()
            return super_areas, distances * earth_radius
        else:
            indcs = self.ball_tree.query(
                np.deg2rad(coordinates),
                return_distance=return_distance,
                k=k,
                sort_results=True,
            )
            indcs = chain.from_iterable(indcs)
            super_areas = [self[idx] for idx in indcs]
            return super_areas

    def get_closest_super_area(self, coordinates):
        return self.get_closest_super_areas(coordinates, k=1, return_distance=False)[0]


class ExternalSuperArea:
    """
    This a city that lives outside the simulated domain.
    """

    external = True
    __slots__ = "city", "spec", "id", "domain_id"

    def __init__(self, id, domain_id):
        self.city = None
        self.spec = "super_area"
        self.id = id
        self.domain_id = domain_id


class Region:
    """
    Coarsest geographical resolution
    """

    __slots__ = ("id", "name", "super_areas")
    _id = count()

    def __init__(
        self, name: Optional[str] = None, super_areas: List[SuperAreas] = None,
    ):
        self.id = next(self._id)
        self.name = name
        self.super_areas = super_areas or []

    @property
    def people(self):
        return list(
            chain.from_iterable(super_area.people for super_area in self.super_areas)
        )


class Regions:
    __slots__ = "members_by_id", "members_by_name"

    def __init__(self, regions: List[Region]):
        self.members_by_id = {region.id: region for region in regions}
        try:
            self.members_by_name = {region.name: region for region in regions}
        except AttributeError:
            self.members_by_name = None

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    def get_from_id(self, id):
        return self.members_by_id[id]

    @property
    def members(self):
        return list(self.members_by_id.values())


class Geography:
    def __init__(
        self, areas: List[Area], super_areas: List[SuperArea], regions: List[Region]
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
        self.households = None
        self.schools = None
        self.hospitals = None
        self.companies = None
        self.care_homes = None
        self.pubs = None
        self.cinemas = None
        self.groceries = None
        self.cemeteries = None
        self.universities = None

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
            areas = [Area(area_coords.name, super_area, area_coords.values)]
        else:
            areas = []
            for name, coordinates in area_coords.iterrows():
                areas.append(
                    Area(
                        name,
                        super_area,
                        coordinates=np.array(
                            [coordinates.latitude, coordinates.longitude]
                        ),
                    )
                )
        return areas

    @classmethod
    def _create_super_areas(
        cls,
        super_area_coords: pd.DataFrame,
        area_coords: pd.DataFrame,
        region: "Region",
        hierarchy: pd.DataFrame,
    ) -> List[Area]:
        """
        Applies the _create_super_area function throught the super_area_coords dataframe.
        If super_area_coords is a series object, then it does not use the apply()
        function as it does not support the axis=1 parameter.

        Parameters
        ----------
        super_area_coords
            pandas Dataframe with the super area name as index and the coordinates
            X, Y where X is longitude and Y is latitude.
        region
            region instance to what all the super areas belong to
        """
        # if a single area is given, then area_coords is a series
        # and we cannot do iterrows()
        area_hierarchy = hierarchy.reset_index()
        area_hierarchy.set_index("super_area", inplace=True)
        total_areas_list, super_areas_list = [], []
        if isinstance(super_area_coords, pd.Series):
            super_areas_list = [
                SuperArea(
                    super_area_coords.name,
                    areas=None,
                    region=region,
                    coordinates=np.array(
                        [super_area_coords.latitude, super_area_coords.longitude]
                    ),
                )
            ]
            areas_df = area_coords.loc[
                area_hierarchy.loc[super_area_coords.name, "area"]
            ]
            areas_list = cls._create_areas(areas_df, super_areas_list[0])
            super_areas_list[0].areas = areas_list
            total_areas_list += areas_list
        else:
            for super_area_name, row in super_area_coords.iterrows():
                super_area = SuperArea(
                    areas=None,
                    name=super_area_name,
                    coordinates=np.array([row.latitude, row.longitude]),
                    region=region,
                )
                areas_df = area_coords.loc[area_hierarchy.loc[super_area_name, "area"]]
                areas_list = cls._create_areas(areas_df, super_area)
                super_area.areas = areas_list
                total_areas_list += list(areas_list)
                super_areas_list.append(super_area)
        return super_areas_list, total_areas_list

    @classmethod
    def create_geographical_units(
        cls,
        hierarchy: pd.DataFrame,
        area_coordinates: pd.DataFrame,
        super_area_coordinates: pd.DataFrame,
        sort_identifiers=True,
    ):
        """
        Create geo-graph of the used geographical units.

        """
        # this method ensure that super geo.super_areas, geo.areas, and so are ordered by identifier.
        region_hierarchy = hierarchy.reset_index().set_index("region")["super_area"]
        region_hierarchy = region_hierarchy.drop_duplicates()
        region_list = []
        total_areas_list, total_super_areas_list = [], []
        for region_name in region_hierarchy.index.unique():
            region = Region(name=region_name, super_areas=None)

            super_areas_df = super_area_coordinates.loc[
                region_hierarchy.loc[region_name]
            ]
            super_areas_list, areas_list = cls._create_super_areas(
                super_areas_df, area_coordinates, region, hierarchy=hierarchy
            )
            region.super_areas = super_areas_list
            total_super_areas_list += list(super_areas_list)
            total_areas_list += list(areas_list)
            region_list.append(region)
        if sort_identifiers:
            total_areas_list = sort_geo_unit_by_identifier(total_areas_list)
            total_super_areas_list = sort_geo_unit_by_identifier(total_super_areas_list)

        areas = Areas(total_areas_list)
        super_areas = SuperAreas(total_super_areas_list)
        regions = Regions(region_list)
        logger.info(
            f"There are {len(areas)} areas and "
            + f"{len(super_areas)} super_areas "
            + f"and {len(regions)} in the world."
        )
        return areas, super_areas, regions

    @classmethod
    def from_file(
        cls,
        filter_key: Optional[Dict[str, list]] = None,
        hierarchy_filename: str = default_hierarchy_filename,
        area_coordinates_filename: str = default_area_coord_filename,
        super_area_coordinates_filename: str = default_superarea_coord_filename,
        sort_identifiers=True,
    ) -> "Geography":
        """
        Load data from files and construct classes capable of generating
        hierarchical structure of geographical areas.

        Example usage
        -------------
            ```
            geography = Geography.from_file(filter_key={"region" : "North East"})
            geography = Geography.from_file(filter_key={"super_area" : ["E02005728"]})
            ```
        Parameters
        ----------
        filter_key
            Filter out geo-units which should enter the world.
            At the moment this can only be one of [area, super_area, region]
        hierarchy_filename
            Pandas df file containing the relationships between the different
            geographical units.
        area_coordinates_filename:
            coordinates of the area units
        super_area_coordinates_filename
            coordinates of the super area units
        logging_config_filename
            file path of the logger configuration
        """
        geo_hierarchy = pd.read_csv(hierarchy_filename)
        areas_coord = pd.read_csv(area_coordinates_filename)
        super_areas_coord = pd.read_csv(super_area_coordinates_filename)
        if filter_key is not None:
            geo_hierarchy = _filtering(geo_hierarchy, filter_key)
        areas_coord = areas_coord.loc[areas_coord.area.isin(geo_hierarchy.area)]
        super_areas_coord = super_areas_coord.loc[
            super_areas_coord.super_area.isin(geo_hierarchy.super_area)
        ].drop_duplicates()
        areas_coord.set_index("area", inplace=True)
        super_areas_coord.set_index("super_area", inplace=True)
        geo_hierarchy.set_index("super_area", inplace=True)
        areas, super_areas, regions = cls.create_geographical_units(
            geo_hierarchy,
            areas_coord,
            super_areas_coord,
            sort_identifiers=sort_identifiers,
        )
        return cls(areas, super_areas, regions)


def _filtering(data: pd.DataFrame, filter_key: Dict[str, list],) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    return data[
        data[list(filter_key.keys())[0]].isin(list(filter_key.values())[0]).values
    ]


def sort_geo_unit_by_identifier(geo_units):
    geo_identifiers = [unit.name for unit in geo_units]
    sorted_idx = np.argsort(geo_identifiers)
    first_unit_id = geo_units[0].id
    units_sorted = [geo_units[idx] for idx in sorted_idx]
    # reassign ids
    for i, unit in enumerate(units_sorted):
        unit.id = first_unit_id + i
    return units_sorted
