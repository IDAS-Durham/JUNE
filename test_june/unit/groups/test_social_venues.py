import numpy as np
from june.groups import SocialVenue, SocialVenues
from june.geography import Geography, SuperAreas


def test__social_venue_from_coordinates():
    super_areas = ["E02004935", "E02004940"] 
    geo = Geography.from_file({"msoa" : super_areas})
    coordinate_list = np.array([[51.752179, -0.334667], [51.741485, -0.336645]])
    social_venues = SocialVenues.from_coordinates(coordinate_list)
    social_venues.add_to_super_areas(geo.super_areas)
    assert len(social_venues) == 2
    assert social_venues[0].super_area == geo.super_areas[0]
    assert social_venues[1].super_area == geo.super_areas[1]

