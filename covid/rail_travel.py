import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import rv_discrete
from tqdm import tqdm

def distribute_passengers(city_travel, peak_commute = None, subtract_commute = False):
    """
    :param city_travel: pd.DataFrame with columns=['station','arrivals','departures','average']
    :param peak_commut: peak commuting data for each station in the morning

    city_travel['station']: strings - all stations in dataset
    city_travel['arrivals]: float - daily arrivals for each station
    city_travel['departures]: float = daily departures for each station
    city_travel['average']: flaot - average of daily arrivals and departures for each station
    """

    # We assume that all stations are connected to each other directly for initial 4testing

    stations = np.array(city_travel['station'])

    arrivals = np.array(city_travel['arrivals'])
    departures = np.array(city_travel['departures'])

    # subtract commuters
    average = np.array(city_travel['average'])
    # Take average and scale by 100 for code testing
    city_travel['average'] = np.array(city_travel['average'])/100.
    # Initialise
    city_travel['arrived'] = np.zeros(len(stations))

    if subtract_commute == False:
        city_travel['to_depart'] = city_travel['average']
        pbar = tqdm(total=np.sum(city_travel['average']))
    else:
        peak_commute = list(peak_commute['commuters'])
        city_travel['average_no_commute'] = average - np.array(peak_commute)
        city_travel['average_no_commute'] = np.array(city_travel['average_no_commute'])/100.
        city_travel['to_depart'] = city_travel['average_no_commute']
        pbar = tqdm(total=np.sum(city_travel['average_no_commute']))

    # Travel matrix is added to for each starting and stopping city
    # Rows are stating city and columns are stopping
    travel_matrix = np.zeros(len(stations)**2).reshape(len(stations),len(stations))

    finished = False
                                                       
    while finished == False:

        city_to_depart = np.array(city_travel['to_depart'])
        city_to_depart[city_to_depart <= 0.] = 1.
        # Get distirbution over people departing
        # distribution = np.array(city_travel['to_depart'])/np.sum(np.array(city_travel['to_depart']))
        distribution = city_to_depart/np.sum(city_to_depart)
        numbers = np.arange(len(distribution))
        # Initialise discrete probability distributionn
        random_variable = rv_discrete(values=(numbers,distribution))
        departing = np.zeros(len(distribution))
        # This can simple be optimised by making size=100 and assigning numbers
        for i in range(10):
            station_id = random_variable.rvs(size=1)
            departing[station_id] +=1

        # Loop through all stations from which to depart
        for station_idx, num_to_travel in enumerate(departing):
            # Stations they can travel to
            travel_stations = np.delete(np.array(city_travel['station']),station_idx)
            if subtract_commute == False:
                travel_average = np.delete(np.array(city_travel['average']),station_idx)
            else:
                travel_average = np.delete(np.array(city_travel['average_no_commute']),station_idx)
            travel_arrived = np.delete(np.array(city_travel['arrived']),station_idx)
            travel_to_depart = np.delete(np.array(city_travel['to_depart']),station_idx)
            # How many people are left to arrive at each station
            travel_to_arrive = travel_average-travel_arrived
            # This is used to form another discrete probability distribution from which
            # the number could risk being negative if not corrected
            # Hacky fix
            travel_to_arrive[travel_to_arrive <= 0.] = 1.
            if np.sum(travel_to_arrive) == len(travel_to_arrive):
                finished = True
                break

            # Set up distribution of stations to travel to
            distribution = travel_to_arrive/np.sum(travel_to_arrive)
            numbers = np.arange(len(distribution))
            random_variable = rv_discrete(values=(numbers,distribution))

            # Loop over the number of people travelling
            for i in range(int(num_to_travel)):
                station_id = random_variable.rvs(size=1)
                travel_station = travel_stations[station_id][0]
                travel_idx = np.where(city_travel['station'] == travel_station)[0][0]
                # Update arrived array
                city_travel['arrived'][travel_idx] += 1
                city_travel['to_depart'][travel_idx] -= 1
                travel_matrix[station_idx][travel_idx] += 1
                #print ('adding 1 to {}'.format(travel_matrix[station_idx][city_travel['station'] == travel_station][0]))
                #print (travel_matrix[station_idx])
                #print (travel_matrix[city_travel['station'] == travel_station])
                travel_matrix[travel_idx][station_idx] += 1
                #print ('adding 1 to {}'.format(travel_matrix[city_travel['station'] == travel_station][0][station_idx]))
            # Update to deoart array to record that people have departed from the station
            city_travel['to_depart'][station_idx] -= num_to_travel

            pbar.update(num_to_travel)

        # Check if otherwise finished
        if len(np.unique(city_travel['to_depart'])) > 1:
            pass
        else:
            finished = True
    pbar.close()

    return travel_matrix, city_travel


if __name__ == "__main__":

    # Read in national travel data
    city_travel = pd.read_csv('../custom_data/major_city_rail_2011.csv')
    peak_commuters = pd.read_csv('../custom_data/major_city_rail_commuters_2016.csv')

    travel_matrix, _ = distribute_passengers(city_travel=city_travel,peak_commute=peak_commuters,subtract_commute=True)

    # Save travel matrix
    np.save('../custom_data/travel_matrix.npy', travel_matrix)
    for row_label, row in zip(list(city_travel['station']), travel_matrix):
        print ('%s [%s]' % (row_label, ' '.join('%02s' % i for i in row)))

    # Normalise travel matrix
    travel = travel_matrix.copy()
    for idx, i in enumerate(travel):
        travel[idx] = i/np.sum(i)
    np.save('../custom_data/travel_matrix_normalised.npy', travel)
    
    # The city_travel dataframe and travel_matrix have now been updated
    # Note: the travel_matrix is not symmetric as it only accounts for the travel from origin to destination and not back again
