import googlemaps
import time

import responses
import requests

class APICall():
    """
    Handling API calls to the Google Maps API
    Interacts through url API calls directly, as well as using the Python client
    
    Note: This requires the Google Maps Place API for running and making calls
    """

    def __init__(self, key):
        self.key = key
        self.client = googlemaps.Client(self.key)
        self.raise_warning()

    def raise_warning(self):
        print ('WARNING: By running this class you will be making Google Maps API calls \n This will use API credits and may charge you money - please proceed with caution')

    def get_request(self, url):
        try:
            response = requests.get(url)
            return response
        except:
            raise Exception('Error: GET request failed')
        
    def process_results(self, results):
        locations = []
        names = []
        reviews = []
        ratings = []
        for i in results:
            locations.append(i['geometry']['location'])
            names.append(i['name'])
            #ratings.append(i['rating'])
            #reviews.append(i['user_ratings_total'])

        return locations, names, reviews, ratings

    def process_pagetoken(self, resp_json_payload, out):
        locations, names, reviews, ratings = out
        try:
            next_page_token = resp_json_payload['next_page_token']
            return [locations, names, reviews, ratings, next_page_token]

        except:
            print ('No more next page tokens')
            return [locations, names, reviews, ratings]
        
    def nearby_search(self, location, radius, location_type, return_pagetoken = False):
        """
        Searches nearby locations given a location and a radius for particular loction types

        :param location: (tuple of ints) location is a tuple of (latitude, longitude)
        :param radius: (int) meter radius search area around location coordinate
        :param location_type: (string) type of location being searched for
        :param return_pagetoken: (bool) if True and there is anoter page to be generated, then returns token for next page

        Note: location types can be found here: https://developers.google.com/places/supported_types#table1
        """

        lat, lon = location
        lat = str(lat)
        lon = str(lon)
        url = ('https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={},{}&radius={}&type={}&&key={}'.format(lat,lon,radius,location_type,self.key))

        response = self.get_request(url)
        # convert to json
        resp_json_payload = response.json()
        
        results = resp_json_payload['results']

        out = self.process_results(results)

        if return_pagetoken:
            out = self.process_pagetoken(resp_json_payload, out)
            return out
        else:
            return out

        
    def nearby_search_next_page(self, next_page_token, return_pagetoken = False):
        """
        After running nearby search with next_page token, call next page
        :param next_page_token: (string) output from self.nearby_search([...], return_pagetoken = True)
        :param return_pagetoken: (bool) if True and there is anoter page to be generated, then returns token for next page
        """
        
        url = ('https://maps.googleapis.com/maps/api/place/nearbysearch/json?pagetoken={}&key={}'.format(next_page_token,self.key))

        response = self.get_request(url)
        
        # convert to json 
        resp_json_payload = response.json()
        
        results = resp_json_payload['results']

        out = self.process_results(results)

        if return_pagetoken:
            out = self.process_pagetoken(resp_json_payload, out)
            return out
        else:
            return out

    def out_len_check(self, out):
        if len(out) == 5:
            locations, names, reviews, ratings, next_page_token = out
            return next_page_token
        else:
            locations, names, reviews, ratings = out
            return None

    
    def nearby_search_loop(self, location, radius, location_type):
        """
        In cases where there may be multple next pages (up to Google's max 3), run loop over all pages
        :param location: (tuple of ints) location is a tuple of (latitude, longitude)
        :param radius: (int) meter radius search area around location coordinate
        :param location_type: (string) type of location being searched for
        """
        print ('Calling API')
        out = self.nearby_search(location, radius, location_type, return_pagetoken = True)
        token = self.out_len_check(out)
        outs = []
        outs.append(out)
        while token is not None:
            print ('Calling API')
            time.sleep(2)
            out_token = self.nearby_search_next_page(token, return_pagetoken = True)
            outs.append(out_token)
            token_check = self.out_len_check(out_token)
            token = token_check

        return outs
        

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
                    #language-"en-UK",
                    type=location_type
                )
            else:
                call = self.client.places(
                    query,
                    location=location,
                    radius=radius,
                    region="UK",
                    #language-"en-UK"
                )

        except:
            raise Exception('Error: GET request failed')

        results = call['results']

        locations, names, reviews, ratings = process_results(results)

        return [locations, names, reviews, ratings]
            

    def distance(self, origin_location, destination_location, mode):
        """
        Determine distance between two locations according t the mode of transport

        :param origin_location: (tuple of ints) origin location is a tuple of (latitude, longitude)
        :param destination_location: (tuple of ints) destination location is a tuple of (latitude, longitude)
        :param mode: (string) mode of transport valid values are “driving”, “walking”, “transit” or “bicycling”
        """

        dist = self.client.distance_matrix(origin_location, destination_location, mode)


        ## TODO finish this if needed

        return dist        
        
        

    
