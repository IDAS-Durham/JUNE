import numpy as np
import pandas as pd

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

    regions = ['East']#'Yorkshire', 'London', 'Wales', 'EastMidlands', 'WestMidlands', 'SouthEast', 'SouthWest', 'NorthEast', 'NorthWest', 'East']
    for region in regions:
        print ('Working on region: {}'.format(region))
        region_file = np.load('outs_{}.npy'.format(region), allow_pickle=True)
        msoa_file = pd.read_csv('msoa_{}.csv'.format(region))
        df_clean = clean(region_file, msoa_file)
        df_clean.to_csv('./outs_{}_clean.csv')
