import math
import numpy as np
earth_radius = 6371  # km

def haversine_distance(origin, destination):
    """
    Taken from https://gist.github.com/rochacbruno/2883505
    # Author: Wayne Dyck
    """
    lat1, lon1 = origin
    lat2, lon2 = destination

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = earth_radius * c
    return d

def add_distance_to_lat_lon(latitude, longitude, x, y):
    """
    Given a latitude and a longitude (in degrees), and two distances (x, y) in km, adds those distances
    to lat and lon
    """
    lat2 = latitude + 180 * y / (earth_radius * np.pi)
    lon2 = longitude + 180 * x / (earth_radius * np.pi * np.cos(latitude))
    return lat2, lon2
