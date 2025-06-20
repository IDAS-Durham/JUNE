import logging
from itertools import count, chain
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import random
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
default_area_socioeconomic_index_filename = (
    paths.data_path / "input/geography/socioeconomic_index.csv"
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
        "socioeconomic_index",
        "airports",
    )
    _id = count()

    def __init__(
        self,
        name: str = None,
        super_area: "SuperArea" = None,
        coordinates: Tuple[float, float] = None,
        socioeconomic_index: float = None,
    ):
        """
        Coordinate is given in the format [Y, X] where X is longitude and Y is latitude.
        """
        self.id = next(self._id)
        self.name = name
        self.care_home = None
        self.coordinates = coordinates
        self.super_area = super_area
        self.socioeconomic_index = socioeconomic_index
        self.people = []
        self.schools = []
        self.households = []
        self.social_venues = {}
        self.airports = []

    def __repr__(self):
        coordinates_repr = self.coordinates if not isinstance(self.coordinates, np.ndarray) else self.coordinates.tolist()
        super_area_repr = f"SuperArea(id={self.super_area.id})" if self.super_area else "None"
        return (
            f"Area(id={self.id}, name={self.name}, coordinates={coordinates_repr}, "
            f"super_area={super_area_repr}, socioeconomic_index={self.socioeconomic_index}, "
            f"people={self.people}, schools={self.schools}, households={self.households}, "
            f"social_venues={self.social_venues})"
        )

    def add(self, person: Person):
        self.people.append(person)
        person.area = self

    def populate(self, demography, ethnicity=True, comorbidity=True):
        for person in demography.populate(
            self.name, ethnicity=ethnicity, comorbidity=comorbidity
        ):
            self.add(person)

    @property
    def region(self):
        return self.super_area.region


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

    def __repr__(self):
        # Create a summary with the number of areas and their IDs
        areas_repr = ", ".join(str(area.id) for area in self.members_by_id.values())
        return f"Areas({len(self.members_by_id)} areas: [{areas_repr}])"

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
        all_members = self.members
        coordinates = np.array([np.deg2rad(area.coordinates) for area in all_members])
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
                all_areas = self.members
                areas = [all_areas[idx] for idx in indcs[0]]
                return areas, distances[0] * earth_radius
            else:
                all_areas = self.members
                areas = [all_areas[idx] for idx in indcs[:, 0]]
                return areas, distances[:, 0] * earth_radius
        else:
            indcs = self.ball_tree.query(
                np.deg2rad(coordinates), return_distance=return_distance, k=k
            )
            all_areas = self.members
            areas = [all_areas[idx] for idx in indcs.flatten()]
            return areas

    def get_closest_area(self, coordinates, return_distance=False):
        if return_distance:
            closest_areas, dists = self.get_closest_areas(
                coordinates, k=1, return_distance=return_distance
            )
            return closest_areas[0], dists[0]
        else:
            return self.get_closest_areas(
                coordinates, k=1, return_distance=return_distance
            )[0]

    def get_bounds(self) -> dict:
        """Get geographical bounds of all areas"""
        if not self.members:
            return {
                "min_lat": -90, "max_lat": 90,
                "min_lon": -180, "max_lon": 180
            }
            
        coordinates = np.array([area.coordinates for area in self.members])
        return {
            "min_lat": coordinates[:, 0].min(),
            "max_lat": coordinates[:, 0].max(),
            "min_lon": coordinates[:, 1].min(),
            "max_lon": coordinates[:, 1].max()
        }


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

    def __repr__(self):
        areas_repr = f"[{len(self.areas)} Area objects]"  # Simplified to avoid recursion
        coordinates_repr = self.coordinates if not isinstance(self.coordinates, np.ndarray) else self.coordinates.tolist()
        return (
            f"SuperArea(id={self.id}, name={self.name}, coordinates={coordinates_repr}, "
            f"region={self.region}, areas={areas_repr}, workers={self.workers}, "
            f"companies={self.companies}, closest_hospitals={self.closest_hospitals})"
        )

    def add_worker(self, person: Person):
        self.workers.append(person)
        person.work_super_area = self

    def remove_worker(self, person: Person):
        self.workers.remove(person)
        person.work_super_area = None

    @property
    def people(self):
        return list(chain.from_iterable(area.people for area in self.areas))

    @property
    def households(self):
        return list(chain.from_iterable(area.households for area in self.areas))

    def __eq__(self, other):
        return self.name == other.name


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

    def __repr__(self):
        # Create a summary with the number of super areas and their IDs
        super_areas_repr = ", ".join(str(super_area.id) for super_area in self.members_by_id.values())
        return f"SuperAreas({len(self.members_by_id)} super areas: [{super_areas_repr}])"

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
        all_members = self.members
        coordinates = np.array(
            [np.deg2rad(super_area.coordinates) for super_area in all_members]
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
            all_super_areas = self.members
            super_areas = [all_super_areas[idx] for idx in indcs]
            distances = distances.flatten()
            return super_areas, distances * earth_radius
        else:
            indcs = self.ball_tree.query(
                np.deg2rad(coordinates),
                return_distance=return_distance,
                k=k,
                sort_results=True,
            )
            all_super_areas = self.members
            super_areas = [all_super_areas[idx] for idx in indcs.flatten()]
            return super_areas

    def get_closest_super_area(self, coordinates, return_distance=False):
        if return_distance:
            closest_areas, distances = self.get_closest_super_areas(
                coordinates, k=1, return_distance=return_distance
            )
            return closest_areas[0], distances[0]
        else:
            return self.get_closest_super_areas(
                coordinates, k=1, return_distance=return_distance
            )[0]


class ExternalSuperArea:
    """
    This a city that lives outside the simulated domain.
    """

    external = True
    __slots__ = "city", "spec", "id", "domain_id", "coordinates"

    def __init__(self, id, domain_id, coordinates):
        self.city = None
        self.spec = "super_area"
        self.id = id
        self.domain_id = domain_id
        self.coordinates = coordinates


class Region:
    """
    Coarsest geographical resolution
    """

    __slots__ = ("id", "name", "super_areas", "policy")
    _id = count()

    def __init__(
        self, name: Optional[str] = None, super_areas: List[SuperAreas] = None
    ):
        self.id = next(self._id)
        self.name = name
        self.super_areas = super_areas or []
        self.policy = {
            "regional_compliance": 1.0,
            "lockdown_tier": None,
            "local_closed_venues": set(),
            "global_closed_venues": set(),
        }

    def __repr__(self):
        # Print a simplified version of each SuperArea in super_areas
        super_areas_repr = ", ".join(f"SuperArea(id={super_area.id})" for super_area in self.super_areas)
        return (
            f"Region(id={self.id}, name={self.name}, super_areas=[{super_areas_repr}], "
            f"policy={self.policy})"
        )
    
    @property
    def people(self):
        return list(
            chain.from_iterable(super_area.people for super_area in self.super_areas)
        )

    @property
    def regional_compliance(self):
        return self.policy["regional_compliance"]

    @regional_compliance.setter
    def regional_compliance(self, value):
        self.policy["regional_compliance"] = value

    @property
    def closed_venues(self):
        return self.policy["local_closed_venues"] | self.policy["global_closed_venues"]

    @property
    def households(self):
        return list(
            chain.from_iterable(
                super_area.households for super_area in self.super_areas
            )
        )


class Regions:
    __slots__ = "members_by_id", "members_by_name"

    def __init__(self, regions: List[Region]):
        self.members_by_id = {region.id: region for region in regions}
        try:
            self.members_by_name = {region.name: region for region in regions}
        except AttributeError:
            self.members_by_name = None

    def __repr__(self):
        # Create a summary with the number of regions and their IDs
        regions_repr = ", ".join(str(region.id) for region in self.members_by_id.values())
        return f"Regions({len(self.members_by_id)} regions: [{regions_repr}])"

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
        self.airports = None  # Initialize airports attribute

    def __repr__(self):
        # Simplify the repr for areas and super_areas to avoid recursion
        areas_repr = ", ".join(f"Area(id={area.id})" for area in self.areas)
        super_areas_repr = ", ".join(f"SuperArea(id={super_area.id})" for super_area in self.super_areas)
        regions_repr = ", ".join(f"Region(id={region.id})" for region in self.regions)

        return (
            f"Geography(\n"
            f"  Areas: [{areas_repr}],\n"
            f"  Super Areas: [{super_areas_repr}],\n"
            f"  Regions: [{regions_repr}],\n"
            f"  Households: {self.households},\n"
            f"  Schools: {self.schools},\n"
            f"  Hospitals: {self.hospitals},\n"
            f"  Companies: {self.companies},\n"
            f"  Care Homes: {self.care_homes},\n"
            f"  Pubs: {self.pubs},\n"
            f"  Cinemas: {self.cinemas},\n"
            f"  Groceries: {self.groceries},\n"
            f"  Cemeteries: {self.cemeteries},\n"
            f"  Universities: {self.universities}\n"
            f")"
        )
    
    @classmethod
    def _create_areas(
        cls,
        area_coords: pd.DataFrame,
        super_area: pd.DataFrame,
        socioeconomic_indices: pd.Series,
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
            areas = [
                Area(
                    area_coords.name,
                    super_area,
                    area_coords.values,
                    socioeconomic_indices.loc[area_coords.name],
                )
            ]
        else:
            areas = []
            for name, coordinates in area_coords.iterrows():
                areas.append(
                    Area(
                        name, #name of the area
                        super_area, #super_area object sent in the constructor
                        coordinates=np.array(
                            [coordinates.latitude, coordinates.longitude]
                        ), #selects the lat and lon of that area
                        socioeconomic_index=socioeconomic_indices.loc[name],
                    )
                )
       
        return areas

    @classmethod
    def _create_super_areas(
        cls,
        super_area_coords: pd.DataFrame,
        area_coords: pd.DataFrame,
        area_socioeconomic_indices: pd.Series,
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
        
        area_hierarchy = hierarchy.reset_index() #sets index to 0-759
        area_hierarchy.set_index("super_area", inplace=True) #removes index and makes super_area column the index
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
            areas_list = cls._create_areas(
                areas_df, super_areas_list[0], area_socioeconomic_indices
            )
            super_areas_list[0].areas = areas_list
            total_areas_list += areas_list
        else: #in the create_world, it always enters here because it has more than 1 area
            for super_area_name, row in super_area_coords.iterrows():
                super_area = SuperArea(
                    areas=None,
                    name=super_area_name,
                    coordinates=np.array([row.latitude, row.longitude]),
                    region=region,
                ) #It creates a super_area object for the super_area name found in the coordinates list
                areas_df = area_coords.loc[area_hierarchy.loc[super_area_name, "area"]] 
                '''
                area_hierarchy.loc[super_area_name, "area"] looks like this:
                basiically it groups all areas within a super area together
                E02000218    E00005617
                E02000218    E00005609
                E02000218    E00005641
                E02000218    E00005625

                then, it locates the coordinates for the areas with area_coords.loc[area_hierarchy.loc[super_area_name, "area"]]
                area  latitude  longitude                          
                E00090542  52.223555   0.123139
                E00090559  52.224415   0.124315
                E00090554  52.225641   0.123566
                
                '''
                areas_list = cls._create_areas(
                    areas_df, super_area, area_socioeconomic_indices
                ) 
                '''
                Basically it sends the areas that belong to this super area, the super area object
                itself, and the SE idx for each area

                and the result areas_list looks like a list of the areas in the super area like this:
                [Area(id=728, name=E00090542, coordinates=[52.22355488857611, 0.123139278108161], 
                super_area=SuperArea(id=28), socioeconomic_index=0.47, people=[], schools=[], 
                households=[], social_venues={})] [Area...]
                '''

                super_area.areas = areas_list 

                ''' 
                It is then stored in the areas attribute of the object itself
                , then a list of the total areas is created appending each iteration
                , same for the super_areas, being a list of super_area objects created
                '''
                total_areas_list += list(areas_list) 
                super_areas_list.append(super_area)
        '''
        Final return, the list of all the super_areas objects, and a list of all the areas objects
        each super_area object contains a list of objects of its areas
        and each area object contains a link to the super_area object it belongs to
        '''

        return super_areas_list, total_areas_list

    @classmethod
    def create_geographical_units(
        cls,
        hierarchy: pd.DataFrame,
        area_coordinates: pd.DataFrame,
        super_area_coordinates: pd.DataFrame,
        area_socioeconomic_indices: pd.Series,
        sort_identifiers=True,
    ):
        """
        Create geo-graph of the used geographical units.

        """
        # this method ensure that super geo.super_areas, geo.areas, and so are ordered by identifier.
        region_hierarchy = hierarchy.reset_index().set_index("region")["super_area"]
        region_hierarchy = region_hierarchy.drop_duplicates()

        '''
        Region_hierarchy looks like this:
        region
        South West         E02002991
        South West         E02002989
        South West         E02002992
        South West         E02002990
        South West         E02002988
        London             E02000218
        '''

        region_list = []
        total_areas_list, total_super_areas_list = [], []
        for region_name in region_hierarchy.index.unique():
            region = Region(name=region_name, super_areas=None)

            '''
            region looks like this: 
            Region(id=0, name=South West, super_areas=[], policy={'regional_compliance': 1.0, 
            'lockdown_tier': None, 'local_closed_venues': set(), 'global_closed_venues': set()})
            '''
            super_areas_df = super_area_coordinates.loc[
                region_hierarchy.loc[region_name]
            ]

            ''' super_areas_df looks like this:              
            super_area  latitude  longitude
            E02002991   51.382708  -2.358340 '''    

            super_areas_list, areas_list = cls._create_super_areas(
                super_areas_df,
                area_coordinates,
                area_socioeconomic_indices,
                region,
                hierarchy=hierarchy,
            )
            region.super_areas = super_areas_list
            total_super_areas_list += list(super_areas_list)
            total_areas_list += list(areas_list)
            region_list.append(region)
        if sort_identifiers:
            #Sort lists by ID
            total_areas_list = sort_geo_unit_by_identifier(total_areas_list)
            total_super_areas_list = sort_geo_unit_by_identifier(total_super_areas_list)

        areas = Areas(total_areas_list)
        super_areas = SuperAreas(total_super_areas_list)
        regions = Regions(region_list)
        logger.info(
            f"There are {len(areas)} areas and "
            + f"{len(super_areas)} super_areas "
            + f"and {len(regions)} regions in the world."
        )

        # Sample visualization
        """ print("\n===== Sample of Created Geographical Units =====")

        # Sample 3 areas and create a DataFrame
        sample_areas = random.sample(total_areas_list, 3)
        areas_data = [{
            "| Area": area.name,
            "| Coordinates": area.coordinates,
            "| Socioeconomic Index": area.socioeconomic_index
        } for area in sample_areas]
        areas_df = pd.DataFrame(areas_data)
        print("\nSample Areas DataFrame:")
        print(areas_df)

        # Sample 3 super areas and create a DataFrame
        sample_super_areas = random.sample(total_super_areas_list, 3)
        super_areas_data = [{
            "| Super Area": super_area.name,
            "| Coordinates": super_area.coordinates,
            "| Number of Areas": len(super_area.areas)
        } for super_area in sample_super_areas]
        super_areas_df = pd.DataFrame(super_areas_data)
        print("\nSample Super Areas DataFrame:")
        print(super_areas_df)

        # Sample 3 regions and create a DataFrame
        sample_regions = random.sample(region_list, 3)
        regions_data = [{
            "| Region": region.name,
            "| Number of Super Areas": len(region.super_areas)
        } for region in sample_regions]
        regions_df = pd.DataFrame(regions_data)
        print("\nSample Regions DataFrame:")
        print(regions_df) """
        
        return areas, super_areas, regions

    @classmethod
    def from_file(
        cls,
        filter_key: Optional[Dict[str, list]] = None,
        hierarchy_filename: str = default_hierarchy_filename,
        area_coordinates_filename: str = default_area_coord_filename,
        super_area_coordinates_filename: str = default_superarea_coord_filename,
        area_socioeconomic_index_filename: str = default_area_socioeconomic_index_filename,
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
        area_socioeconomic_index_filename
            socioeconomic index of each area
        logging_config_filename
            file path of the logger configuration
        """
        try:
            # Safely load all the required files
            try:
                geo_hierarchy = pd.read_csv(hierarchy_filename)
                logger.info(f"Successfully loaded hierarchy from {hierarchy_filename}")
            except Exception as e:
                logger.error(f"Failed to load hierarchy file: {e}")
                raise GeographyError(f"Failed to load hierarchy file: {e}")

            try:
                areas_coord = pd.read_csv(area_coordinates_filename)
                logger.info(f"Successfully loaded area coordinates from {area_coordinates_filename}")
            except Exception as e:
                logger.error(f"Failed to load area coordinates file: {e}")
                raise GeographyError(f"Failed to load area coordinates file: {e}")

            try:
                super_areas_coord = pd.read_csv(super_area_coordinates_filename)
                logger.info(f"Successfully loaded super area coordinates from {super_area_coordinates_filename}")
            except Exception as e:
                logger.error(f"Failed to load super area coordinates file: {e}")
                raise GeographyError(f"Failed to load super area coordinates file: {e}")

            # Check if the required columns exist in the dataframes
            required_columns = {
                "geo_hierarchy": ["area", "super_area", "region"],
                "areas_coord": ["area", "latitude", "longitude"],
                "super_areas_coord": ["super_area", "latitude", "longitude"]
            }

            for df_name, cols in required_columns.items():
                df = locals()[df_name]
                missing_cols = [col for col in cols if col not in df.columns]
                if missing_cols:
                    error_msg = f"Missing required columns in {df_name}: {missing_cols}"
                    logger.error(error_msg)
                    raise GeographyError(error_msg)

            # Apply filtering if provided
            if filter_key is not None:
                if not isinstance(filter_key, dict):
                    logger.warning(f"filter_key should be a dictionary, got {type(filter_key)}. Converting to dict.")
                    try:
                        filter_key = dict(filter_key)
                    except Exception as e:
                        logger.error(f"Could not convert filter_key to dictionary: {e}")
                        raise GeographyError(f"filter_key must be a dictionary, got {type(filter_key)}")
                
                # Check if filter_key has valid keys (area, super_area, or region)
                valid_keys = ["area", "super_area", "region"]
                if not any(key in valid_keys for key in filter_key.keys()):
                    logger.warning(f"filter_key must contain one of {valid_keys}. Got {list(filter_key.keys())}")
                
                try:
                    geo_hierarchy = _filtering(geo_hierarchy, filter_key)
                    if geo_hierarchy.empty:
                        logger.warning(f"Filtering resulted in empty geography. Check filter_key: {filter_key}")
                except Exception as e:
                    logger.error(f"Error applying filter: {e}")
                    raise GeographyError(f"Error applying filter: {e}")

            # Filter coordinates based on hierarchy
            areas_coord = areas_coord.loc[areas_coord.area.isin(geo_hierarchy.area)]
            super_areas_coord = super_areas_coord.loc[
                super_areas_coord.super_area.isin(geo_hierarchy.super_area)
            ].drop_duplicates()

            # Check if filtering resulted in empty dataframes
            if areas_coord.empty:
                logger.error("No matching areas found after filtering")
                raise GeographyError("No matching areas found after filtering")
            if super_areas_coord.empty:
                logger.error("No matching super areas found after filtering")
                raise GeographyError("No matching super areas found after filtering")

            # Set up indices for the coordinate dataframes
            areas_coord.set_index("area", inplace=True)
            areas_coord = areas_coord[["latitude", "longitude"]]
            super_areas_coord.set_index("super_area", inplace=True)
            super_areas_coord = super_areas_coord[["latitude", "longitude"]]
            geo_hierarchy.set_index("super_area", inplace=True)
            
            # Load socioeconomic data if available
            if area_socioeconomic_index_filename:
                try:
                    area_socioeconomic_df = pd.read_csv(area_socioeconomic_index_filename)
                    area_socioeconomic_df = area_socioeconomic_df.loc[
                        area_socioeconomic_df.area.isin(geo_hierarchy.area)
                    ]
                    if area_socioeconomic_df.empty:
                        logger.warning("No matching socioeconomic data found after filtering, using default values")
                        area_socioeconomic_index = pd.Series(
                            data=np.full(len(areas_coord), 0.5),  # Default to middle value
                            index=areas_coord.index,
                            name="socioeconomic_centile",
                        )
                    else:
                        area_socioeconomic_df.set_index("area", inplace=True)
                        if "socioeconomic_centile" not in area_socioeconomic_df.columns:
                            logger.warning("'socioeconomic_centile' column not found in socioeconomic data, using default values")
                            area_socioeconomic_index = pd.Series(
                                data=np.full(len(areas_coord), 0.5),
                                index=areas_coord.index,
                                name="socioeconomic_centile",
                            )
                        else:
                            area_socioeconomic_index = area_socioeconomic_df["socioeconomic_centile"]
                except Exception as e:
                    logger.warning(f"Error loading socioeconomic data: {e}. Using default values.")
                    area_socioeconomic_index = pd.Series(
                        data=np.full(len(areas_coord), 0.5),
                        index=areas_coord.index,
                        name="socioeconomic_centile",
                    )
            else:
                # If no socioeconomic file provided, use default values
                area_socioeconomic_index = pd.Series(
                    data=np.full(len(areas_coord), 0.5),
                    index=areas_coord.index,
                    name="socioeconomic_centile",
                )
            
            # Create geographical units
            try:
                areas, super_areas, regions = cls.create_geographical_units(
                    geo_hierarchy,
                    areas_coord,
                    super_areas_coord,
                    area_socioeconomic_index,
                    sort_identifiers=sort_identifiers,
                )
            except Exception as e:
                logger.error(f"Error creating geographical units: {e}")
                raise GeographyError(f"Error creating geographical units: {e}")

            logger.info(f"Successfully created Geography with {len(areas)} areas, {len(super_areas)} super areas, and {len(regions)} regions")
            return cls(areas, super_areas, regions)

        except Exception as e:
            logger.error(f"Unexpected error in Geography.from_file: {e}")
            raise GeographyError(f"Failed to create geography: {e}")


def _filtering(data: pd.DataFrame, filter_key: Dict[str, list]) -> pd.DataFrame:
    """
    Filter DataFrame for given geo-unit and it's listed names
    """
    try:
        filter_unit = list(filter_key.keys())[0]
        filter_values = list(filter_key.values())[0]
        
        # Ensure filter_values is a list
        if not isinstance(filter_values, list):
            logger.warning(f"filter_values should be a list, converting {filter_values} to list")
            if isinstance(filter_values, str):
                filter_values = [filter_values]
            else:
                try:
                    filter_values = list(filter_values)
                except Exception:
                    filter_values = [filter_values]
        
        # Check if filter_unit is in the dataframe columns
        if filter_unit not in data.columns:
            available_columns = data.columns.tolist()
            logger.error(f"Filter unit '{filter_unit}' not in available columns: {available_columns}")
            raise GeographyError(f"Filter unit '{filter_unit}' not in available columns: {available_columns}")
        
        # Apply the filter
        filtered_data = data[data[filter_unit].isin(filter_values)]
        
        # Check if the filter resulted in an empty dataframe
        if filtered_data.empty:
            logger.warning(f"Filtering by {filter_unit}={filter_values} resulted in empty dataset")
        
        return filtered_data
    except IndexError:
        logger.error("filter_key dictionary is empty or improperly formatted")
        raise GeographyError("filter_key dictionary is empty or improperly formatted")
    except Exception as e:
        logger.error(f"Error in _filtering: {e}")
        raise GeographyError(f"Error in _filtering: {e}")


def sort_geo_unit_by_identifier(geo_units):
    geo_identifiers = [unit.name for unit in geo_units]
    sorted_idx = np.argsort(geo_identifiers)
    first_unit_id = geo_units[0].id
    units_sorted = [geo_units[idx] for idx in sorted_idx]
    # reassign ids
    for i, unit in enumerate(units_sorted):
        unit.id = first_unit_id + i
    return units_sorted
