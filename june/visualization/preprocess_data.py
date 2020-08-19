import numpy as np
import pandas as pd
import sys
from tqdm import tqdm

from june.logger.read_logger import ReadLogger

results_path = sys.argv[1]

read_logger = ReadLogger(output_path = results_path, load_real = False)

print ('####### Loading super area summary #########')
super_area_summary = read_logger.super_area_summary()
print ('####### Super area summary loaded #########')

super_area_summary.to_csv(results_path + '/super_area_summary.csv')

super_area_summary = super_area_summary.reset_index()

print ('####### Extracting relevant information from dates #########')

date = []
for idx, row in super_area_summary.iterrows():
    date.append(row['time_stamp'].date())
super_area_summary['date'] = date

dates = np.unique(super_area_summary['date'])
super_areas = np.unique(super_area_summary['super_area'])

indices = []
for super_area in tqdm(super_areas):
    super_area_data = super_area_summary[super_area_summary['super_area'] == super_area]
    for date in dates:
        indices.append(super_area_data[super_area_data['date'] == date].index[-1])

out_df = super_area_summary.loc[indices]

out_df.reset_index(inplace=True)

out_df.to_csv(results_path + '/super_area_summary_clean.csv')
