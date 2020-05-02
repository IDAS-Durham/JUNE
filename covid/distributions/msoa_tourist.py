import numpy as np
import pandas as pd

from gmapi import APICall

def get_msoas_tourist(apikey, msoas):

    apicall = APICall(apikey)

    coordinates = []
    for i in range(len(msoas)):
        coordinates.append((msoas['Y'][i],msoas['X'][i]))
    outs = []
    for i in range(len(coordinates)):
        out = apicall.nearby_search_loop(location=(coordinates[i][0],coordinates[i][1]),radius=4600,location_type='tourist_attraction')
        outs.append(out)

    return outs


if __name__ == "__main__":

    with open('/Users/josephbullock/Desktop/GMAPIkey.txt', 'r') as f:
        api = f.read()
    apikey = api.split('\n')[0]

    regions = ['Yorkshire', 'London', 'Wales']
        #'EastMidlands', 'WestMidlands', 'SouthEast', 'SouthWest', 'NorthEast', 'NorthWest', 'East']

    for region in regions:
        print ('Working on region: {}'.format(region))
        msoas = pd.read_csv('./../../custom_data/msoa_coordinates_{}.csv'.format(region))
        outs = get_msoas_tourist(apikey,msoas)
        np.save('./../../custom_data/outs_{}'.format(region), outs)
