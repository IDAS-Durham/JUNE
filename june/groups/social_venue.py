import numpy as np
from typing import List
from enum import IntEnum
from sklearn.neighbors import BallTree
from june.groups import Supergroup, Group, Subgroup
from june.geography import Area, SuperArea, SuperAreas


class SocialVenueError(BaseException):
    pass


class SocialVenue(Group):
    class SubgroupType(IntEnum):
        default = 0

    def __init__(self):
        super().__init__()


class SocialVenues(Supergroup):
    def __init__(self, social_venues: List[SocialVenue]):
        super().__init__()
        self.members = social_venues

    @classmethod
    def from_coordinates(cls, coordinates: List[np.array]):
        social_venues = list()
        for coord in coordinates:
            sv = SocialVenue()
            sv.coordinates = coord
            social_venues.append(sv)
        return cls(social_venues)

    @classmethod
    def for_areas(cls, areas: List[Area], venues_per_area=1):
        """
        Generates social venues in the given areas.

        Parameters
        ----------
        areas
            list of areas to generate the venues in
        venues_per_area
            how many venus per area to generate
        """
        social_venues = []
        for area in areas:
            for _ in range(0, venues_per_area):
                sv = SocialVenue()
                sv.area = area
                social_venues.append(sv)
        return cls(social_venues)

    @classmethod
    def for_super_areas(cls, super_areas: List[SuperArea], venues_per_super_area=1):
        """
        Generates social venues in the given super areas.

        Parameters
        ----------
        super_areas
            list of areas to generate the venues in
        venues_per_super_area
            how many venus per super_area to generate
        """
        social_venues = []
        for super_area in super_areas:
            for _ in range(0, venues_per_super_area):
                sv = SocialVenue()
                sv.super_area = super_area
                social_venues.append(sv)
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
            venue.super_area = super_areas.get_super_area(venue.coordinates)
