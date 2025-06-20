import numpy as np
import pandas as pd
import logging
import random
from typing import List, Optional
from enum import IntEnum
from sklearn.neighbors import BallTree

from june.epidemiology.infection.disease_config import DiseaseConfig
from june.groups import Supergroup, Group
from june.geography import Area, Areas, SuperArea, SuperAreas, Geography
from june.mpi_wrapper import mpi_rank, mpi_available

earth_radius = 6371  # km

logger = logging.getLogger("social_venue")
# Only disable propagation in MPI mode with rank > 0
if mpi_available and mpi_rank > 0:
    logger.propagate = False


class SocialVenueError(BaseException):
    pass


class SocialVenue(Group):
    max_size = np.inf

    def __init__(self, area=None):
        super().__init__()  # Pass disease_config to the parent class
        self.area = area
        # Use 0 as domain_id in non-MPI mode
        self.domain_id = 0 if not mpi_available else mpi_rank
        

    def add(self, person, activity="leisure"):
        self.subgroups[0].append(person)
        setattr(person.subgroups, activity, self.subgroups[0])

    @property
    def super_area(self):
        return self.area.super_area

    @property
    def get_coordinates(self):
        if self.area is None:
            return
        else:
            return self.area.coordinates

    # def get_leisure_subgroup(self, person, subgroup_type, to_send_abroad):
    #     return self[self.SubgroupType.leisure]


class SocialVenues(Supergroup):
    venue_class = SocialVenue

    def __init__(self, social_venues: List[venue_class], make_tree=True):
        super().__init__(members=social_venues)
        # Use a safer logging approach that works in both MPI and non-MPI modes
        current_rank = 0 if not mpi_available else mpi_rank
        logger.info(f"Domain {current_rank} has {len(self)} {self.spec}(s)")
        self.ball_tree = None
        if make_tree:
            if not social_venues:
                logger.warning(f"No social venues of type {self.spec} in this domain")
            else:
                self.make_tree()

    @classmethod
    def from_coordinates(
        cls,
        coordinates: List[np.array],
        super_areas: Optional[Areas],
        max_distance_to_area=10,
        **kwargs,
    ):
        if len(coordinates) == 0:
            return cls([], **kwargs)

        if super_areas:
            super_areas, distances = super_areas.get_closest_super_areas(
                coordinates, k=1, return_distance=True
            )
            distances_close = np.where(distances < max_distance_to_area)
            coordinates = coordinates[distances_close]
        social_venues = []

        for i, coord in enumerate(coordinates):
            sv = cls.venue_class()  # Pass disease_config here
            if super_areas:
                super_area = super_areas[i]
            else:
                super_area = None
            sv.coordinates = coord
            if super_areas:
                area, dist = Areas(super_area.areas).get_closest_area(
                    coordinates=coord, return_distance=True
                )

                if dist > max_distance_to_area:
                    continue

                sv.area = area
            social_venues.append(sv)

        return cls(social_venues, **kwargs)

    @classmethod
    def for_super_areas(
        cls, super_areas: List[SuperArea], coordinates_filename: str = None
    ):
        if coordinates_filename is None:
            coordinates_filename = cls.default_coordinates_filename
        sv_coordinates = pd.read_csv(coordinates_filename, index_col=0).values

        # Generate social venues using the coordinates
        social_venues_instance = cls.from_coordinates(
            sv_coordinates, super_areas=super_areas
        )

        # Prepare sample data for visualization
        venue_data = [
            {
                "Venue ID": venue.id,
                "Super Area": venue.area.super_area.name if venue.area and venue.area.super_area else "Unknown",
                "Coordinates": venue.coordinates,
                "Assigned Area": venue.area.name if venue.area else "None",
            }
            for venue in social_venues_instance.members
        ]

        # Convert sample data to DataFrame for better readability
        df_venues = pd.DataFrame(venue_data)
        print("\n===== Gaps in ID represent the venues that were created that did not fulfill the criteria required =====")
        print("\n===== Sample of Social Venues Created from Coordinates =====")
        print(df_venues)

        return social_venues_instance


    @classmethod
    def for_areas(cls, areas: Areas, coordinates_filename: str = None):
        if coordinates_filename is None:
            coordinates_filename = cls.default_coordinates_filename
        super_areas = SuperAreas([area.super_area for area in areas])
        return cls.for_super_areas(super_areas, coordinates_filename)

    @classmethod
    def for_geography(cls, geography: Geography, coordinates_filename: str = None):
        if coordinates_filename is None:
            coordinates_filename = cls.default_coordinates_filename
        
        return cls.for_super_areas(geography.super_areas, coordinates_filename)

    @classmethod
    def distribute_for_areas(
        cls,
        areas: List[Area],
        venues_per_capita: float = None,
        venues_per_area: int = None,
    ):
        """
        Generates social venues in the given areas.

        Parameters
        ----------
        areas
            list of areas to generate the venues in
        venues_per_capita
            number of venues per person in each area.
        venues_per_area
            number of venues in each area.
        """
        if venues_per_area is not None and venues_per_capita is not None:
            raise SocialVenueError(
                "Please specify only one of venues_per_capita or venues_per_area."
            )
        social_venues = []
        if venues_per_area is not None:
            for area in areas:
                for _ in range(venues_per_area):
                    sv = cls.venue_class()
                    sv.area = area
                    social_venues.append(sv)
        elif venues_per_capita is not None:
            for area in areas:
                area_population = len(area.people)
                for _ in range(int(np.ceil(venues_per_capita * area_population))):
                    sv = cls.venue_class()
                    sv.area = area
                    sv.coordinates = area.coordinates
                    social_venues.append(sv)
        else:
            raise SocialVenueError(
                "Specify one of venues_per_capita or venues_per_area"
            )
        return cls(social_venues)

    @classmethod
    def distribute_for_super_areas(
        cls, super_areas: List[SuperArea], venues_per_super_area=1, venues_per_capita=1
    ):
        """
        Generates social venues in the given super areas.

        Parameters
        ----------
        super_areas
            list of areas to generate the venues in
        venues_per_super_area
            how many venus per super_area to generate
        """
        if venues_per_super_area is not None and venues_per_capita is not None:
            raise SocialVenueError(
                "Please specify only one of venues_per_capita or venues_per_area."
            )
        social_venues = []
        if venues_per_super_area is not None:
            for area in super_areas:
                for _ in range(venues_per_super_area):
                    sv = cls.venue_class()
                    sv.area = area
                    social_venues.append(sv)
        elif venues_per_capita is not None:
            for super_area in super_areas:
                super_area_population = len(super_area.people)
                for _ in range(int(np.ceil(venues_per_capita * super_area_population))):
                    sv = cls.venue_class()
                    area = Areas(super_area.areas).get_closest_area(
                        coordinates=super_area.coordinates
                    )
                    sv.area = area
                    sv.coordinates = area.coordinates
                    social_venues.append(sv)
        else:
            raise SocialVenueError(
                "Specify one of venues_per_capita or venues_per_area"
            )
        return cls(social_venues)

    def make_tree(self):
        self.ball_tree = BallTree(
            np.array([np.deg2rad(sv.coordinates) for sv in self]), metric="haversine"
        )

    def add_to_areas(self, areas: Areas):
        """
        Adds all venues to the closest super area
        """
        for venue in self:
            if not hasattr(venue, "coordinates"):
                raise SocialVenueError(
                    "Can't add to super area if venues don't have coordiantes."
                )
            venue.area = areas.get_closest_areas(venue.coordinates)[0]

    def get_closest_venues(self, coordinates, k=1):
        """
        Queries the ball tree for the closests venues.

        Parameters
        ----------
        coordinates
            coordinates in the format [Latitude, Longitude]
        k
            number of neighbours desired
        """
        if not self.members:
            return
        if self.ball_tree is None:
            raise SocialVenueError("Initialise ball tree first with self.make_tree()")
        venue_idxs = self.ball_tree.query(
            np.deg2rad(coordinates).reshape(1, -1), return_distance=False, k=k
        ).flatten()
        social_venues = self.members
        return [social_venues[idx] for idx in venue_idxs]

    def get_venues_in_radius(self, coordinates, radius=5):
        """
        Queries the ball tree for the closests venues.

        Parameters
        ----------
        coordinates
            coordinates in the format [Latitude, Longitude]
        radius
            radius in km to query
        """
        if not self.members:
            return
        if self.ball_tree is None:
            raise SocialVenueError("Initialise ball tree first with self.make_tree()")
        radius = radius / earth_radius
        venue_idxs, _ = self.ball_tree.query_radius(
            np.deg2rad(coordinates).reshape(1, -1),
            r=radius,
            sort_results=True,
            return_distance=True,
        )
        venue_idxs = venue_idxs[0]
        if not venue_idxs.size:
            return None
        social_venues = self.members
        return [social_venues[idx] for idx in venue_idxs]

    def get_leisure_subgroup(self, person, subgroup_type, to_send_abroad):
        return self[subgroup_type]