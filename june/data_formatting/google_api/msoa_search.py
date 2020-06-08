import numpy as np
import pandas as pd
import argparse

from gmapi import APICall

class MSOASearch():
    """
    Functions for running Google Maps API by region at the MSOA level for a given type

    More information on Google types can be found here: https://developers.google.com/places/supported_types
    """
    
    def __init__(self):
        self.args = self.parse()

    def parse(self):
        '''
        Parse input arguments
        '''
        parser = argparse.ArgumentParser(description='Run the Google Maps API by region at the MSOA level for a given type')
        parser.add_argument(
            '--apikey_file',
            dest='apikey_file',
            help='location of txt file containing apikey',
            type=str
        )
        
        parser.add_argument(
            '--type',
            dest='location_type',
            help='Google maps type being selected (found on Google Cloud documentation)',
            type=str
        )

        parser.add_argument(
            '--msoa_coord_dir',
            dest='msoa_coord',
            help='directory containing MSOA centroids - assume also where file will be saved to',
            type=str
        )
        
        args = parser.parse_args()

        return args

    def get_msoas_type(self, apikey, msoas):
        '''
        For a given type, call Google Maps API to search for type
        
        Note: Currently the radius is fixed at the average required to cover the whole of England and Wales
        '''
        self.apikey = apikey
        apicall = APICall(self.apikey)

        coordinates = []
        for i in range(len(msoas)):
            coordinates.append((msoas['Y'][i],msoas['X'][i]))
        outs = []
        for i in range(len(coordinates)):
            out = apicall.nearby_search_loop(location=(coordinates[i][0],coordinates[i][1]),radius=4600,location_type=self.args.location_type)
            outs.append(out)
            #print (out)

        return outs


if __name__ == "__main__":

    msoasearch = MSOASearch()

    with open(msoasearch.args.apikey_file, 'r') as f:
        api = f.read()
    apikey = api.split('\n')[0]

    regions = ['East']#, 'SouthEast', 'SouthWest', 'NorthEast', 'NorthWest', 'Yorkshire','London', 'Wales', 'EastMidlands', 'WestMidlands']

    for region in regions:
        print ('Working on region: {}'.format(region))
        msoas = pd.read_csv('{}/msoa_coordinates_{}.csv'.format(msoasearch.args.msoa_coord,region))
        outs = msoasearch.get_msoas_type(apikey,msoas)
        np.save('{}/outs_{}_{}.npy'.format(msoasearch.args.msoa_coord, msoasearch.args.location_type, region), outs, allow_pickle=True)
