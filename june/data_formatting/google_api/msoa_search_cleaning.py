import numpy as np
import pandas as pd
import argparse

def parse():
    '''
    Parse input arguments
    '''
    parser = argparse.ArgumentParser(description='Clean Google Maps API data pulled using msoa_search.py')

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
    
def clean(region_file, msoa_file):

    msoa = []
    latitude = []
    longitude = []
    name = []
    for idx, i in enumerate(region_file):
        for j in i:
            for k in j[0]:
                latitude.append(k['lat'])
                longitude.append(k['lng'])
            for k in j[1]:
                name.append(k)
                msoa.append(list(msoa_file['MSOA11CD'])[idx])

    data = {'lat': latitude, 'lon': longitude, 'name': name, 'msoa': msoa}
    df = pd.DataFrame(data)

    df_drop = df.drop_duplicates(subset=['lat','lon'], keep="first")

    return df_drop


if __name__ == "__main__":

    args = parse()

    regions = ['Yorkshire', 'London', 'Wales', 'EastMidlands', 'WestMidlands', 'SouthEast', 'SouthWest', 'NorthEast', 'NorthWest', 'East']
    for region in regions:
        print ('Working on region: {}'.format(region))
        region_file = np.load('{}/outs_{}_{}.npy'.format(args.msoa_coord, args.location_type, region), allow_pickle=True)
        msoa_file = pd.read_csv('{}/msoa_coordinates_{}.csv'.format(args.msoa_coord, region))
        df_clean = clean(region_file, msoa_file)
        df_clean.to_csv('{}/outs_{}_{}_clean.csv'.format(args.msoa_coord, args.location_type, region))
