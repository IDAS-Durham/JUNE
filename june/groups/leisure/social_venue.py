import numpy as np
from typing import List, Optional
from enum import IntEnum
from sklearn.neighbors import BallTree
from june.groups import Supergroup, Group, Subgroup
from june.demography.geography import Area, Areas, SuperArea, SuperAreas

earth_radius = 6371  # km


class SocialVenueError(BaseException):
    pass


class SocialVenue(Group):
    class SubgroupType(IntEnum):
        default = 0

    def __init__(self, max_size=np.inf):
        super().__init__()
        self.max_size = max_size

    def add(self, person, activity="leisure"):
        self.subgroups[0].append(person)
        setattr(person.subgroups, activity, self.subgroups[0])

    def get_leisure_subgroup(self, person):
        return self.subgroups[0]


class SocialVenues(Supergroup):
    def __init__(self, social_venues: List[SocialVenue]):
        super().__init__()
        self.ball_tree = None
        self.members = social_venues

    @classmethod
    def from_coordinates(
        cls,
        coordinates: List[np.array],
        areas: Optional[Areas] = None,
        max_distance_to_area=5,
        **kwargs
    ):

        if areas is not None:
            _, distances = areas.get_closest_areas(
                coordinates, k=1, return_distance=True
            )
            distances_close = np.where(distances < max_distance_to_area)
            coordinates = coordinates[distances_close]
        social_venues = list()
        for coord in coordinates:
            sv = SocialVenue()
            sv.coordinates = coord
            social_venues.append(sv)
        return cls(social_venues, **kwargs)

    @classmethod
    def for_areas(
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
                    sv = SocialVenue()
                    sv.area = area
                    social_venues.append(sv)
        elif venues_per_capita is not None:
            for area in areas:
                area_population = len(area.people)
                for _ in range(int(np.ceil(venues_per_capita * area_population))):
                    sv = SocialVenue()
                    sv.area = area
                    social_venues.append(sv)
        else:
            raise SocialVenueError(
                "Specify one of venues_per_capita or venues_per_area"
            )
        return cls(social_venues)

    @classmethod
    def for_super_areas(
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
                    sv = SocialVenue()
                    sv.area = area
                    social_venues.append(sv)
        elif venues_per_capita is not None:
            for area in super_areas:
                area_population = len(area.people)
                for _ in range(int(np.ceil(venues_per_capita * area_population))):
                    sv = SocialVenue()
                    sv.area = area
                    social_venues.append(sv)
        else:
            raise SocialVenueError(
                "Specify one of venues_per_capita or venues_per_area"
            )
        return cls(social_venues)

    def make_tree(self):
        self.ball_tree = BallTree(np.array([np.deg2rad(sv.coordinates) for sv in self]))

    def add_to_super_areas(self, super_areas: SuperAreas):
        """
        Adds all venues to the closest super area
        """
        for venue in self:
            if not hasattr(venue, "coordinates"):
                raise SocialVenueError(
                    "Can't add to super area if venues don't have coordiantes."
                )
            venue.super_area = super_areas.get_closest_super_areas(venue.coordinates)[0]

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
        if self.ball_tree is None:
            raise SocialVenueError("Initialise ball tree first with self.make_tree()")
        venue_idxs = self.ball_tree.query(
            np.deg2rad(coordinates).reshape(1, -1), return_distance=False, k=k
        ).flatten()
        return [self[idx] for idx in venue_idxs]

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
        return [self[idx] for idx in venue_idxs]
