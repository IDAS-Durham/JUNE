import googlemaps
from datetime import datetime

import responses
import requests

class APICall():

    def __init__(key):
        self.key = key
        self.client = googlemaps.Client(self.key)

    def process_results(self, results):
        locations = []
        names = []
        reviews = []
        ratings = []
        for i in results:
            locations.append(i['geometry']['location'])
            names.append(i['name'])
            ratings.append(i['rating'])
            reviews.append(i['user_ratings_total'])

        return locations, names, reviews, ratings

        
    def nearby_search(self, location, radius, location_type):
        """
        Searches nearby locations given a location and a radius for particular loction types

        :param location: (tuple of ints) location is a tuple of (latitude, longitude)
        :param radius: (int) meter radius search area around location coordinate
        :param location_type: (string) type of location being searched for

        Note: location types can be found here: https://developers.google.com/places/supported_types#table1
        """

        lat, lon = location
        lat = str(lat)
        lon = std(lon)
        url = ('https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={},{}&radius={}&type={}&&key={}'.format(apikey,lat,lon,radius,location_type,self.key))

        try:
            response = requests.get(url)
            pass
        except:
            raise Exception('Error: GET request failed')
        
        # convert to json
        resp_json_payload = response.json()
        results = resp_json_payload['results']

        locations, names, reviews, ratings = self.process_results(results)

        return locations, names, reviews, ratings

        
    def places(self, query, location, radius, location_type = None):
        """
        Search places according to a certain query

        :param query: (string) e.g. 'restaurant'
        :param location: (tuple of ints) location is a tuple of (latitude, longitude)
        :param radius: (int) meter radius search area around location coordinate
        :param location_type: (string, optional) type of location being searched for
        """

        
        try:
            if location_type is not None:
                call = self.client.places(
                    query,
                    location=location,
                    radius=radius,
                    region="UK",
                    language-"en-UK",
                    type=location_type
                )
            else:
                call = self.client.places(
                    query,
                    location=location,
                    radius=radius,
                    region="UK",
                    language-"en-UK"
                )
            pass

        except:
            raise Exception('Error: GET request failed')

        results = call['results']

        locations, names, reviews, ratings = process_results(results)

        return locations, names, reviews, ratings
            
            
        
        

    
