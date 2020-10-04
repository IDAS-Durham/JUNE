import numpy as np
from june.groups.leisure import SocialVenue, SocialVenues
from june.geography import Geography, SuperAreas


def test__social_venue_from_coordinates():
    super_areas = ["E02004935", "E02004940"] 
    geo = Geography.from_file({"super_area" : super_areas})
    coordinate_list = np.array([[51.752179, -0.334667], [51.741485, -0.336645]])
    social_venues = SocialVenues.from_coordinates(coordinate_list, super_areas=geo.super_areas)
    social_venues.add_to_areas(geo.areas)
    assert len(social_venues) == 2
    assert social_venues[0].super_area == geo.super_areas[0]
    assert social_venues[1].super_area == geo.super_areas[1]

def test__get_closest_venues():
    coordinate_list = np.array([[51.752179, -0.334667], [51.741485, -0.336645]])

    social_venues = SocialVenues.from_coordinates(coordinate_list, super_areas=None)
    social_venues.make_tree()
    venue = social_venues.get_closest_venues([50, 0])[0]
    assert venue == social_venues[1]

    venues_in_radius = social_venues.get_venues_in_radius([51.7, -0.33], 10)
    assert venues_in_radius[0] == social_venues[1]
    assert venues_in_radius[1] == social_venues[0]


